"""Shared helpers for FlightClaw - filters, formatting, data persistence."""

import json
import os
from datetime import datetime, timedelta
from itertools import product

from fast_flights import FlightData, Passengers, get_flights
from scripts.search_utils import fmt_price, parse_price_str

SEAT_MAP = {
    "ECONOMY": "economy",
    "PREMIUM_ECONOMY": "premium-economy",
    "BUSINESS": "business",
    "FIRST": "first",
}

STOPS_MAP = {
    "ANY": None,
    "NON_STOP": 0,
    "ONE_STOP": 1,
    "TWO_STOPS": 2,
}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TRACKED_FILE = os.path.join(DATA_DIR, "tracked.json")


def load_tracked():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE, "r") as f:
            return json.load(f)
    return []


def save_tracked(tracked):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TRACKED_FILE, "w") as f:
        json.dump(tracked, f, indent=2)


def expand_routes(origins_str, destinations_str, date_str, date_to_str=None):
    origins = [o.strip().upper() for o in origins_str.split(",")]
    destinations = [d.strip().upper() for d in destinations_str.split(",")]
    start = datetime.strptime(date_str, "%Y-%m-%d").date()
    end = datetime.strptime(date_to_str, "%Y-%m-%d").date() if date_to_str else start
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return list(product(origins, destinations, dates))


def build_flight_data(orig_code, dest_code, date, return_date=None):
    flight_data = [FlightData(date=date, from_airport=orig_code, to_airport=dest_code)]
    trip = "one-way"
    if return_date:
        flight_data.append(FlightData(date=return_date, from_airport=dest_code, to_airport=orig_code))
        trip = "round-trip"
    return flight_data, trip


def search_flights(orig_code, dest_code, date, return_date=None, cabin="ECONOMY", stops="ANY", adults=1, top_n=5):
    flight_data, trip = build_flight_data(orig_code, dest_code, date, return_date)
    result = get_flights(
        flight_data=flight_data,
        trip=trip,
        passengers=Passengers(adults=adults),
        seat=SEAT_MAP.get(cabin, "economy"),
        max_stops=STOPS_MAP.get(stops),
    )
    return result.flights[:top_n], result.current_price


def format_flight(flight, index=None):
    prefix = f"Option {index}: " if index else ""
    ahead = f" (+{flight.arrival_time_ahead})" if flight.arrival_time_ahead else ""
    lines = [
        f"{prefix}{flight.price} | {flight.duration} | {flight.stops} stop(s)",
        f"  {flight.name}: departs {flight.departure} -> arrives {flight.arrival}{ahead}",
    ]
    if flight.delay:
        lines.append(f"  Delay: {flight.delay}")
    return "\n".join(lines)
