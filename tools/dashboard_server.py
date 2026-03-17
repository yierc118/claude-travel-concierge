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
from pydantic import BaseModel
from watchfiles import awatch

BASE_DIR = Path(__file__).parent.parent
TRIPS_DIR = BASE_DIR / "trips"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Travel Concierge Dashboard")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# SSE subscriber queue
_subscribers: list[asyncio.Queue] = []


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
    trip_dir = TRIPS_DIR / trip_id
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
    data = _read_json(TRIPS_DIR / trip_id / "flights.json")
    if data is None:
        raise HTTPException(status_code=404, detail="flights.json not found")
    return data


@app.get("/api/trips/{trip_id}/accommodation")
async def get_accommodation(trip_id: str):
    data = _read_json(TRIPS_DIR / trip_id / "accommodation.json")
    if data is None:
        raise HTTPException(status_code=404, detail="accommodation.json not found")
    return data


@app.get("/api/trips/{trip_id}/budget")
async def get_budget(trip_id: str):
    data = _read_json(TRIPS_DIR / trip_id / "budget.json")
    if data is None:
        raise HTTPException(status_code=404, detail="budget.json not found")
    return data


@app.get("/api/trips/{trip_id}/status")
async def get_status(trip_id: str):
    content = _read_text(TRIPS_DIR / trip_id / "STATUS.md")
    if content is None:
        raise HTTPException(status_code=404, detail="STATUS.md not found")
    return {"content": content}


@app.get("/api/trips/{trip_id}/itinerary")
async def get_itinerary(trip_id: str):
    content = _read_text(TRIPS_DIR / trip_id / "itinerary.md")
    if content is None:
        raise HTTPException(status_code=404, detail="itinerary.md not found")
    return {"content": content}


class ItineraryUpdate(BaseModel):
    content: str


@app.post("/api/trips/{trip_id}/itinerary")
async def update_itinerary(trip_id: str, body: ItineraryUpdate):
    trip_dir = TRIPS_DIR / trip_id
    if not trip_dir.exists():
        raise HTTPException(status_code=404, detail=f"Trip '{trip_id}' not found")
    itinerary_path = trip_dir / "itinerary.md"
    try:
        itinerary_path.write_text(body.content)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to write itinerary: {e}")
    return {"status": "saved"}


if __name__ == "__main__":
    port = int(os.environ.get("DASHBOARD_PORT", 8000))
    print(f"Dashboard running at http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)
