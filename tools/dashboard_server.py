"""
Travel Concierge Dashboard Server
FastAPI + SSE + watchfiles — serves live trip data from /trips directory.
Runs locally on 127.0.0.1 only.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import AsyncGenerator, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from watchfiles import awatch

BASE_DIR = Path(__file__).parent.parent
TRIPS_DIR = BASE_DIR / "trips"
STATIC_DIR = Path(__file__).parent / "static"
HOTELCLAW_TRACKED = BASE_DIR / "skills" / "hotelclaw" / "data" / "tracked.json"
FLIGHTCLAW_TRACKED = BASE_DIR / "skills" / "flightclaw" / "data" / "tracked.json"
CRONS_FILE = BASE_DIR / "crons.json"

app = FastAPI(title="Travel Concierge Dashboard")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# SSE subscriber queue
_subscribers: list[asyncio.Queue] = []


def _safe_trip_dir(trip_id: str) -> Path:
    """Resolve trip directory and reject any path traversal attempts."""
    trip_dir = (TRIPS_DIR / trip_id).resolve()
    if not trip_dir.is_relative_to(TRIPS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid trip ID")
    return trip_dir


def _read_json(path: Path) -> dict | list | None:
    """Read a JSON file, return None if missing or invalid."""
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _read_text(path: Path) -> str | None:
    """Read a text file, return None if missing."""
    try:
        if path.exists():
            return path.read_text()
    except OSError:
        pass
    return None


def _get_trips() -> list[dict]:
    """List all trips with basic info from skeleton.json."""
    trips = []
    if not TRIPS_DIR.exists():
        return trips
    for trip_dir in sorted(TRIPS_DIR.iterdir()):
        if not trip_dir.is_dir():
            continue
        skeleton = _read_json(trip_dir / "skeleton.json")
        if skeleton:
            skeleton["_trip_id"] = trip_dir.name
            trips.append(skeleton)
    return trips


async def _watch_trips():
    """Background task: watch trips/ dir and notify SSE subscribers."""
    async for changes in awatch(str(TRIPS_DIR)):
        event = json.dumps({"type": "trips_updated", "changes": len(changes)})
        dead = []
        for q in _subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _subscribers.remove(q)


@app.on_event("startup")
async def startup():
    TRIPS_DIR.mkdir(exist_ok=True)
    asyncio.create_task(_watch_trips())


@app.get("/", response_class=HTMLResponse)
async def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    return HTMLResponse("<h1>Dashboard loading...</h1>")


@app.get("/events")
async def sse_endpoint(request: Request):
    """Server-Sent Events stream for live updates."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.append(queue)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            yield "data: {\"type\": \"connected\"}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {event}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/trips")
async def list_trips():
    return {"trips": _get_trips()}


@app.get("/api/trips/{trip_id}")
async def get_trip(trip_id: str):
    trip_dir = _safe_trip_dir(trip_id)
    if not trip_dir.exists():
        raise HTTPException(status_code=404, detail=f"Trip '{trip_id}' not found")
    return {
        "skeleton": _read_json(trip_dir / "skeleton.json"),
        "flights": _read_json(trip_dir / "flights.json"),
        "accommodation": _read_json(trip_dir / "accommodation.json"),
        "budget": _read_json(trip_dir / "budget.json"),
        "status": _read_text(trip_dir / "STATUS.md"),
        "itinerary": _read_text(trip_dir / "itinerary.md"),
    }


@app.get("/api/trips/{trip_id}/flights")
async def get_flights(trip_id: str):
    data = _read_json(_safe_trip_dir(trip_id) / "flights.json")
    if data is None:
        raise HTTPException(status_code=404, detail="flights.json not found")
    return data


@app.get("/api/trips/{trip_id}/accommodation")
async def get_accommodation(trip_id: str):
    data = _read_json(_safe_trip_dir(trip_id) / "accommodation.json")
    if data is None:
        raise HTTPException(status_code=404, detail="accommodation.json not found")
    return data


@app.get("/api/flights/all")
async def get_all_flights():
    """Merge flightclaw tracked routes + per-trip flights.json legs, normalised to a common shape."""
    tracked_list = _read_json(FLIGHTCLAW_TRACKED) or []
    trips = _get_trips()

    # Build date-range lookup: trip_id -> (first_arrive, last_depart)
    trip_ranges: dict[str, tuple[str, str]] = {}
    for t in trips:
        cities = t.get("cities", [])
        if cities:
            trip_ranges[t["_trip_id"]] = (
                cities[0].get("arrive", ""),
                cities[-1].get("depart", ""),
            )

    def _find_trip(date_str: str) -> Optional[str]:
        for tid, (arrive, depart) in trip_ranges.items():
            if arrive and depart and arrive <= date_str <= depart:
                return tid
        return None

    result: list[dict] = []
    seen_route_keys: set[str] = set()

    for route in tracked_list:
        date = route.get("date") or ""
        key = f"{route.get('origin')}-{route.get('destination')}-{date}"
        seen_route_keys.add(key)
        normalized_history = [
            {
                "timestamp": h.get("timestamp"),
                "price": h.get("best_price"),
                "airline": h.get("airline"),
                "price_str": h.get("price_str"),
            }
            for h in route.get("price_history", [])
        ]
        result.append(
            {
                "id": route.get("id"),
                "from": route.get("origin"),
                "to": route.get("destination"),
                "date": date,
                "cabin": route.get("cabin"),
                "_trip_id": _find_trip(date),
                "_source": "tracked",
                "booked": route.get("booked", False),
                "target_price": route.get("target_price"),
                "price_history": normalized_history,
            }
        )

    if TRIPS_DIR.exists():
        for trip_dir in sorted(TRIPS_DIR.iterdir()):
            if not trip_dir.is_dir():
                continue
            trip_id = trip_dir.name
            flights = _read_json(trip_dir / "flights.json")
            if not (flights and flights.get("legs")):
                continue
            for leg in flights["legs"]:
                key = f"{leg.get('from')}-{leg.get('to')}-{leg.get('date')}"
                if key in seen_route_keys:
                    continue  # already in tracked
                normalized_history = [
                    {
                        "timestamp": h.get("timestamp"),
                        "price": h.get("price") or h.get("price_sgd") or h.get("best_price"),
                        "price_str": h.get("price_str"),
                    }
                    for h in leg.get("price_history", [])
                ]
                result.append(
                    {
                        "id": key,
                        "from": leg.get("from"),
                        "to": leg.get("to"),
                        "date": leg.get("date"),
                        "cabin": leg.get("cabin"),
                        "_trip_id": trip_id,
                        "_source": "researched",
                        "booked": leg.get("booked", False),
                        "target_price": None,
                        "price_history": normalized_history,
                        "options": leg.get("options", []),
                    }
                )

    return {"flights": result}


@app.get("/api/hotels/all")
async def get_all_hotels():
    """Merge per-trip accommodation.json options + hotelclaw tracked.json prices."""
    tracked_list = _read_json(HOTELCLAW_TRACKED) or []
    tracked_by_name: dict[str, dict] = {t["name"].lower(): t for t in tracked_list}

    def _find_tracked(name: str) -> dict | None:
        """Match by exact name or prefix substring (handles short vs long name variants)."""
        nl = name.lower()
        if nl in tracked_by_name:
            return tracked_by_name[nl]
        for tname, tdata in tracked_by_name.items():
            if nl in tname or tname.startswith(nl):
                return tdata
        return None

    result: list[dict] = []
    tracked_seen: set[str] = set()

    if TRIPS_DIR.exists():
        for trip_dir in sorted(TRIPS_DIR.iterdir()):
            if not trip_dir.is_dir():
                continue
            trip_id = trip_dir.name
            accomm = _read_json(trip_dir / "accommodation.json")
            if not accomm:
                continue

            # Normalise to a flat list of (option_dict, city, check_in, check_out, nights)
            raw_options: list[tuple[dict, str, str | None, str | None, int | None]] = []

            # Format A: top-level "options" list (Bangkok style)
            if accomm.get("options"):
                city = accomm.get("city", "")
                for opt in accomm["options"]:
                    raw_options.append(
                        (opt, opt.get("city") or city, accomm.get("check_in"), accomm.get("check_out"), accomm.get("nights"))
                    )

            # Format B: "cities[].options" list (Japan style)
            elif accomm.get("cities"):
                for city_block in accomm["cities"]:
                    for opt in city_block.get("options") or []:
                        raw_options.append(
                            (
                                opt,
                                opt.get("city") or city_block.get("city", ""),
                                city_block.get("arrive"),
                                city_block.get("depart"),
                                city_block.get("nights"),
                            )
                        )

            for opt, city, check_in, check_out, nights in raw_options:
                name_lower = opt.get("name", "").lower()
                tracked = _find_tracked(opt.get("name", ""))
                if tracked:
                    tracked_seen.add(tracked["name"].lower())
                result.append(
                    {
                        "name": opt.get("name"),
                        "city": city,
                        "check_in": check_in,
                        "check_out": check_out,
                        "nights": nights,
                        "_trip_id": trip_id,
                        "_source": "tracked" if tracked else "research",
                        "nightly_rate_usd": opt.get("nightly_rate_usd"),
                        "url": opt.get("booking_url") or (tracked.get("url") if tracked else None),
                        "booked": opt.get("booked", False) or (tracked.get("booked", False) if tracked else False),
                        "target_price": tracked.get("target_price") if tracked else None,
                        "price_history": tracked.get("price_history", []) if tracked else [],
                        "notes": opt.get("notes"),
                    }
                )

    # Build check_in date → trip_id fallback for orphan tracked properties
    trips_list = _get_trips()
    checkin_to_trip: dict[str, str] = {}
    for t in trips_list:
        arrive = (t.get("cities") or [{}])[0].get("arrive")
        if arrive:
            checkin_to_trip[arrive] = t["_trip_id"]

    # Include tracked properties not matched to any accommodation.json option
    for t in tracked_list:
        if t["name"].lower() not in tracked_seen:
            orphan_trip = checkin_to_trip.get(t.get("check_in", ""))
            result.append(
                {
                    "name": t.get("name"),
                    "city": t.get("city"),
                    "check_in": t.get("check_in"),
                    "check_out": t.get("check_out"),
                    "nights": t.get("nights"),
                    "_trip_id": orphan_trip,
                    "_source": "tracked",
                    "nightly_rate_usd": None,
                    "url": t.get("url"),
                    "booked": t.get("booked", False),
                    "target_price": t.get("target_price"),
                    "price_history": t.get("price_history", []),
                    "notes": None,
                }
            )

    return {"hotels": result}


@app.get("/api/hotels/tracked")
async def get_tracked_hotels():
    """Return all hotelclaw-tracked properties with full price history."""
    data = _read_json(HOTELCLAW_TRACKED)
    return {"tracked": data or []}


@app.get("/api/trips/{trip_id}/budget")
async def get_budget(trip_id: str):
    data = _read_json(_safe_trip_dir(trip_id) / "budget.json")
    if data is None:
        raise HTTPException(status_code=404, detail="budget.json not found")
    return data


@app.get("/api/trips/{trip_id}/status")
async def get_status(trip_id: str):
    content = _read_text(_safe_trip_dir(trip_id) / "STATUS.md")
    if content is None:
        raise HTTPException(status_code=404, detail="STATUS.md not found")
    return {"content": content}


@app.get("/api/trips/{trip_id}/itinerary")
async def get_itinerary(trip_id: str):
    content = _read_text(_safe_trip_dir(trip_id) / "itinerary.md")
    if content is None:
        raise HTTPException(status_code=404, detail="itinerary.md not found")
    return {"content": content}


class ItineraryUpdate(BaseModel):
    content: str = Field(max_length=500_000)


@app.post("/api/trips/{trip_id}/itinerary")
async def update_itinerary(trip_id: str, body: ItineraryUpdate):
    trip_dir = _safe_trip_dir(trip_id)
    if not trip_dir.exists():
        raise HTTPException(status_code=404, detail=f"Trip '{trip_id}' not found")
    itinerary_path = trip_dir / "itinerary.md"
    try:
        itinerary_path.write_text(body.content)
    except OSError:
        raise HTTPException(status_code=500, detail="Failed to save itinerary")
    return {"status": "saved"}


def _has_booked_flights() -> bool:
    """Return True if any trip has at least one flight leg with booked=True."""
    if not TRIPS_DIR.exists():
        return False
    for trip_dir in TRIPS_DIR.iterdir():
        if not trip_dir.is_dir():
            continue
        flights = _read_json(trip_dir / "flights.json")
        if not flights:
            continue
        for leg in flights.get("legs", []):
            if leg.get("booked"):
                return True
    return False


@app.get("/api/crons")
async def get_crons():
    """Read system crontab + crons.json planned jobs and return merged list."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "crontab", "-l",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        raw = stdout.decode("utf-8", errors="replace") if stdout else ""
    except (FileNotFoundError, asyncio.TimeoutError, OSError):
        raw = ""

    jobs: list[dict] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 5)
        if len(parts) < 6:
            continue
        schedule_str = " ".join(parts[:5])
        command = parts[5]
        # Label jobs that belong to this project
        is_travel = "AgenticWorflow_Travel" in command or "travel" in command.lower()
        jobs.append(
            {
                "schedule": schedule_str,
                "command": command,
                "status": "active",
                "type": "system",
                "project": "travel" if is_travel else "other",
            }
        )

    # Merge planned/conditional jobs from crons.json
    planned_config = _read_json(CRONS_FILE)
    if planned_config and planned_config.get("planned"):
        booked = _has_booked_flights()
        for entry in planned_config["planned"]:
            condition = entry.get("condition")
            if condition == "booked_flight":
                condition_met = booked
            else:
                condition_met = False
            jobs.append(
                {
                    "id": entry.get("id"),
                    "name": entry.get("name"),
                    "description": entry.get("description"),
                    "schedule": entry.get("schedule"),
                    "schedule_human": entry.get("schedule_human"),
                    "condition_human": entry.get("condition_human"),
                    "condition_met": condition_met,
                    "note": entry.get("note"),
                    "status": "ready" if condition_met else "pending",
                    "type": "planned",
                    "project": "travel",
                }
            )

    return {"jobs": jobs, "raw": raw.strip() or None}


if __name__ == "__main__":
    port = int(os.environ.get("DASHBOARD_PORT", 8000))
    print(f"Dashboard running at http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)
