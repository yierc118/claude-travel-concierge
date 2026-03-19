#!/usr/bin/env python3
"""
Daily travel briefing cron script.

Runs as a standalone cron job — no Claude session required.
For each active trip:
  1. Runs hotelclaw price checks
  2. Reads accommodation shortlist + budget
  3. Classifies prices vs history
  4. Sends HTML briefing email to RECIPIENT
  5. Updates trips/[id]/STATUS.md with last report timestamp

Usage:
    python3 workflows/daily-briefing.py

Crontab (08:00 HKT daily — adjust if system timezone differs from HKT):
    0 8 * * * cd "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge" && source .env && python3 workflows/daily-briefing.py >> /tmp/travel-briefing.log 2>&1
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hotelclaw"))

from tools.gmail_send import send_email, GmailError  # noqa: E402
from helpers import load_tracked, fmt_price           # noqa: E402

TRIPS_DIR = ROOT / "trips"
RECIPIENT = os.environ.get("BRIEFING_RECIPIENT", "caoyier118@gmail.com")


# ── Price classification (from workflows/budget-tracking.md) ─────────────────

def classify_price(current: float, history: list[dict]) -> dict:
    """Returns badge dict with label, emoji, and CSS class."""
    prices = [h["price_per_night"] for h in history if h.get("price_per_night")]
    if len(prices) < 3:
        return {"label": "Tracking", "emoji": "⏳", "color": "#888"}
    avg = sum(prices) / len(prices)
    pct = (current - avg) / avg * 100
    if pct <= -15:
        return {"label": "Buy now", "emoji": "🟢", "color": "#22c55e"}
    elif pct <= -5:
        return {"label": "Good deal", "emoji": "🔵", "color": "#3b82f6"}
    elif pct <= 5:
        return {"label": "Fair", "emoji": "⚪", "color": "#94a3b8"}
    else:
        return {"label": "Above avg", "emoji": "🔴", "color": "#ef4444"}


# ── Data loading ──────────────────────────────────────────────────────────────

def load_active_trips() -> list[dict]:
    trips = []
    if not TRIPS_DIR.exists():
        return trips
    for trip_dir in sorted(TRIPS_DIR.iterdir()):
        skeleton = trip_dir / "skeleton.json"
        if not skeleton.exists():
            continue
        try:
            data = json.loads(skeleton.read_text())
            if data.get("status") == "active":
                data["_trip_dir"] = trip_dir
                trips.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return trips


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def is_stale(timestamp_str: str, hours: int = 18) -> bool:
    """Return True if timestamp is older than `hours` hours."""
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - ts
        return age.total_seconds() > hours * 3600
    except (ValueError, TypeError):
        return True


# ── Hotel price section ───────────────────────────────────────────────────────

def run_price_check() -> tuple[list[dict], list[str]]:
    """
    Run hotelclaw check-prices and return (tracked_entries, warnings).
    Reads directly from the tracked.json after updating prices.
    """
    warnings = []
    script = ROOT / "skills" / "hotelclaw" / "scripts" / "check-prices.py"

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "PYTHONPATH": str(ROOT / "skills" / "hotelclaw")},
        )
        if result.returncode != 0:
            warnings.append(f"⚠️ hotelclaw check-prices exited with code {result.returncode}: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        warnings.append("⚠️ hotelclaw check-prices timed out after 120s")
    except Exception as e:
        warnings.append(f"⚠️ hotelclaw check-prices failed: {e}")

    return load_tracked(), warnings


# ── HTML email builder ────────────────────────────────────────────────────────

def build_email(trips: list[dict], tracked: list[dict], price_warnings: list[str]) -> str:
    today = datetime.now().strftime("%A, %d %B %Y")
    sections = []

    for trip in trips:
        trip_id = trip.get("trip_id", "unknown")
        trip_dir: Path = trip["_trip_dir"]
        cities = trip.get("cities", [])
        city_names = ", ".join(c["name"] for c in cities)
        event = trip.get("event", "")
        first_city = cities[0] if cities else {}
        last_city = cities[-1] if cities else {}
        dates = f"{first_city.get('arrive', '')} – {last_city.get('depart', '')}"

        # Budget
        budget_data = load_json(trip_dir / "budget.json")
        budget_total = budget_data.get("budget_usd")
        items = budget_data.get("items", [])
        committed = sum(i["amount"] for i in items if i.get("type") == "confirmed")
        estimated = sum(i["amount"] for i in items if i.get("type") in ("confirmed", "estimate"))

        budget_html = ""
        if budget_total:
            remaining = budget_total - estimated
            budget_html = f"""
            <table style="width:100%;border-collapse:collapse;margin:8px 0;">
              <tr><td style="color:#94a3b8;padding:2px 0;">Budget</td><td style="text-align:right;">${budget_total:,.0f}</td></tr>
              <tr><td style="color:#94a3b8;padding:2px 0;">Committed</td><td style="text-align:right;">${committed:,.0f}</td></tr>
              <tr><td style="color:#94a3b8;padding:2px 0;">Estimated total</td><td style="text-align:right;">${estimated:,.0f}</td></tr>
              <tr style="border-top:1px solid #334155;"><td style="padding-top:4px;">Remaining</td><td style="text-align:right;font-weight:bold;">${remaining:,.0f}</td></tr>
            </table>"""
        else:
            budget_html = "<p style='color:#94a3b8;margin:4px 0;'>No budget set</p>"

        # Hotel prices for this trip
        trip_hotels = [t for t in tracked if t.get("check_in", "").startswith(first_city.get("arrive", "XXXX")[:7])]
        hotel_rows = ""
        for entry in trip_hotels:
            history = entry.get("price_history", [])
            latest = next((h["price_per_night"] for h in reversed(history) if h.get("price_per_night")), None)
            stale = is_stale(history[-1]["timestamp"]) if history else True
            stale_flag = " ⚠️" if stale else ""

            if latest:
                badge = classify_price(latest, history)
                price_str = f"${latest:.0f}/night"
                badge_html = f'<span style="color:{badge["color"]};font-weight:bold;">{badge["emoji"]} {badge["label"]}</span>'
            else:
                price_str = "No data"
                badge_html = '<span style="color:#888;">⏳ Tracking</span>'

            hotel_rows += f"""
            <tr style="border-bottom:1px solid #1e293b;">
              <td style="padding:6px 4px;">{entry['name']}{stale_flag}</td>
              <td style="padding:6px 4px;text-align:right;">{price_str}</td>
              <td style="padding:6px 4px;text-align:right;">{badge_html}</td>
            </tr>"""

        hotels_html = ""
        if hotel_rows:
            hotels_html = f"""
            <h3 style="color:#94a3b8;font-size:13px;margin:16px 0 6px;text-transform:uppercase;letter-spacing:1px;">Hotels</h3>
            <table style="width:100%;border-collapse:collapse;">
              <thead><tr style="color:#64748b;font-size:12px;">
                <th style="text-align:left;padding:4px;">Property</th>
                <th style="text-align:right;padding:4px;">Rate/night</th>
                <th style="text-align:right;padding:4px;">Signal</th>
              </tr></thead>
              <tbody>{hotel_rows}</tbody>
            </table>"""
        else:
            hotels_html = "<p style='color:#64748b;font-size:13px;margin:8px 0;'>No hotels tracked yet.</p>"

        sections.append(f"""
        <div style="background:#1e293b;border-radius:8px;padding:16px;margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
              <span style="font-size:16px;font-weight:bold;">{city_names}</span>
              {"<span style='color:#94a3b8;font-size:13px;margin-left:8px;'>" + event + "</span>" if event else ""}
            </div>
            <span style="color:#64748b;font-size:12px;">{dates}</span>
          </div>
          <div style="color:#64748b;font-size:12px;margin-top:2px;">{trip_id}</div>
          {hotels_html}
          <h3 style="color:#94a3b8;font-size:13px;margin:16px 0 6px;text-transform:uppercase;letter-spacing:1px;">Budget</h3>
          {budget_html}
        </div>""")

    warnings_html = ""
    all_warnings = price_warnings
    if all_warnings:
        warning_items = "".join(f"<li>{w}</li>" for w in all_warnings)
        warnings_html = f"""
        <div style="background:#422006;border:1px solid #92400e;border-radius:6px;padding:12px;margin-bottom:16px;">
          <strong style="color:#fbbf24;">⚠️ Warnings</strong>
          <ul style="color:#fcd34d;margin:6px 0 0;padding-left:18px;">{warning_items}</ul>
        </div>"""

    body = f"""<!DOCTYPE html>
<html>
<body style="background:#0f172a;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:24px;max-width:600px;margin:0 auto;">
  <div style="margin-bottom:20px;">
    <h1 style="font-size:20px;margin:0;">✈️ Travel Price Report</h1>
    <p style="color:#64748b;margin:4px 0 0;">{today}</p>
  </div>
  {warnings_html}
  {"".join(sections) if sections else '<p style="color:#64748b;">No active trips.</p>'}
  <div style="color:#334155;font-size:11px;margin-top:24px;border-top:1px solid #1e293b;padding-top:12px;">
    Sent by Travel Concierge · ⚠️ = price data older than 18h · Rates in USD
  </div>
</body>
</html>"""
    return body


# ── STATUS.md update ──────────────────────────────────────────────────────────

def update_status(trip_dir: Path, note: str) -> None:
    status_file = trip_dir / "STATUS.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M HKT")
    try:
        content = status_file.read_text() if status_file.exists() else ""
        if "Last Report:" in content:
            lines = content.splitlines()
            lines = [f"Last Report: {now} — {note}" if l.startswith("Last Report:") else l for l in lines]
            status_file.write_text("\n".join(lines) + "\n")
        else:
            status_file.write_text(content.rstrip() + f"\nLast Report: {now} — {note}\n")
    except OSError as e:
        print(f"Warning: could not update STATUS.md for {trip_dir.name}: {e}", file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"[{datetime.now().isoformat()}] daily-briefing starting")

    trips = load_active_trips()
    if not trips:
        print("No active trips found. Exiting.")
        return

    print(f"Active trips: {[t['trip_id'] for t in trips]}")

    tracked, price_warnings = run_price_check()
    if price_warnings:
        for w in price_warnings:
            print(w, file=sys.stderr)

    html = build_email(trips, tracked, price_warnings)
    today_str = datetime.now().strftime("%Y-%m-%d")
    subject = f"✈️ Travel Price Report — {today_str}"

    try:
        msg_id = send_email(RECIPIENT, subject, html, html=True)
        print(f"Email sent to {RECIPIENT} (id: {msg_id})")
        status_note = f"email sent to {RECIPIENT}"
    except GmailError as e:
        print(f"ERROR: Gmail send failed: {e}", file=sys.stderr)
        status_note = f"email FAILED: {e}"
        sys.exit(1)

    for trip in trips:
        update_status(trip["_trip_dir"], status_note)

    print(f"[{datetime.now().isoformat()}] daily-briefing complete")


if __name__ == "__main__":
    main()
