"""
AirLabs API wrapper — flight departure status for booked flights.
Only called day-of for booked flights (costs API credits).
API docs: https://airlabs.co/docs/flight
"""
import os
import requests
from typing import Any


class AirLabsError(Exception):
    pass


def get_flight_status(flight_number: str, date: str) -> dict[str, Any]:
    """
    Get real-time status for a booked flight.

    Args:
        flight_number: IATA flight code, e.g. "SQ321"
        date: departure date in YYYY-MM-DD format

    Returns:
        dict with keys: flight_number, status, dep_time, arr_time,
                        delayed_minutes, terminal, gate
    """
    api_key = os.environ.get("AIRLABS_API_KEY")
    if not api_key:
        raise AirLabsError("AIRLABS_API_KEY environment variable is not set.")

    url = "https://airlabs.co/api/v9/flight"
    params = {"flight_iata": flight_number, "api_key": api_key}

    response = requests.get(url, params=params, timeout=10)

    if response.status_code != 200:
        raise AirLabsError(f"AirLabs API error {response.status_code}: {response.json()}")

    data = response.json().get("response", {})

    return {
        "flight_number": data.get("flight_iata", flight_number),
        "status": data.get("status", "unknown"),
        "dep_time": data.get("dep_time"),
        "arr_time": data.get("arr_time"),
        "delayed_minutes": data.get("delayed", 0) or 0,
        "terminal": data.get("dep_terminal"),
        "gate": data.get("dep_gate"),
    }
