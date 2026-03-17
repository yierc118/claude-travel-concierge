"""
Google Calendar helpers — builds event dicts for use with Google Calendar MCP.
The actual MCP call is made by the agent; this module builds the payload.
"""
from typing import Any


def build_flight_event(
    flight_number: str,
    origin: str,
    destination: str,
    departure_datetime: str,
    arrival_datetime: str,
    confirmation: str = "",
) -> dict[str, Any]:
    """Build a Google Calendar event dict for a flight."""
    description = f"Flight: {flight_number}\nRoute: {origin} → {destination}"
    if confirmation:
        description += f"\nConfirmation: {confirmation}"

    return {
        "summary": f"✈️ {origin} → {destination} ({flight_number})",
        "start": {"dateTime": departure_datetime},
        "end": {"dateTime": arrival_datetime},
        "description": description,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 1440},  # 24h before
                {"method": "popup", "minutes": 180},   # 3h before
            ],
        },
    }


def build_hotel_event(
    hotel_name: str,
    city: str,
    check_in: str,
    check_out: str,
    confirmation: str = "",
) -> dict[str, Any]:
    """Build a Google Calendar event dict for a hotel stay (all-day)."""
    description = f"Hotel: {hotel_name}\nCity: {city}"
    if confirmation:
        description += f"\nConfirmation: {confirmation}"

    return {
        "summary": f"🏨 {hotel_name} ({city})",
        "start": {"date": check_in},
        "end": {"date": check_out},
        "description": description,
    }
