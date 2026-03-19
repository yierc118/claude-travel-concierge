#!/usr/bin/env python3
"""Add a flight route to the price tracking list."""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from itertools import product

from fast_flights import FlightData, Passengers, get_flights
from search_utils import fmt_price, parse_price_str

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

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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


def parse_args():
    parser = argparse.ArgumentParser(description="Track a flight route")
    parser.add_argument("origin", help="Origin airport IATA code(s), comma-separated")
    parser.add_argument("destination", help="Destination airport IATA code(s), comma-separated")
    parser.add_argument("date", help="Departure date (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="End of date range (YYYY-MM-DD)")
    parser.add_argument("--return-date", help="Return date (YYYY-MM-DD)")
    parser.add_argument("--cabin", default="ECONOMY", choices=SEAT_MAP.keys())
    parser.add_argument("--stops", default="ANY", choices=STOPS_MAP.keys())
    parser.add_argument("--target-price", type=float, help="Alert when price drops below this")
    parser.add_argument("--adults", type=int, default=1, help="Number of adult passengers")
    return parser.parse_args()


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


def main():
    args = parse_args()
    combos = expand_routes(args.origin, args.destination, args.date, args.date_to)
    tracked = load_tracked()
    added = 0
    skipped = 0
    currency = "USD"

    for orig_code, dest_code, date in combos:
        route_id = f"{orig_code}-{dest_code}-{date}"
        if args.return_date:
            route_id += f"-RT-{args.return_date}"

        if any(t["id"] == route_id for t in tracked):
            print(f"Already tracking {route_id}")
            skipped += 1
            continue

        print(f"Searching {orig_code} -> {dest_code} on {date}...")

        flight_data = [FlightData(date=date, from_airport=orig_code, to_airport=dest_code)]
        trip = "one-way"
        if args.return_date:
            flight_data.append(FlightData(date=args.return_date, from_airport=dest_code, to_airport=orig_code))
            trip = "round-trip"

        now = datetime.now(timezone.utc).isoformat()
        price_entry = {"timestamp": now, "best_price": None, "airline": None, "price_str": None}

        try:
            result = get_flights(
                flight_data=flight_data,
                trip=trip,
                passengers=Passengers(adults=args.adults),
                seat=SEAT_MAP[args.cabin],
                max_stops=STOPS_MAP[args.stops],
            )
            if result.flights:
                best = result.flights[0]
                price_entry["price_str"] = best.price
                price_entry["best_price"] = parse_price_str(best.price)
                price_entry["airline"] = best.name
        except Exception as e:
            print(f"  Search failed: {e}", file=sys.stderr)

        entry = {
            "id": route_id,
            "origin": orig_code,
            "destination": dest_code,
            "date": date,
            "return_date": args.return_date,
            "cabin": args.cabin,
            "stops": args.stops,
            "target_price": args.target_price,
            "currency": currency,
            "added_at": now,
            "price_history": [price_entry],
        }

        tracked.append(entry)
        added += 1

        if price_entry["price_str"]:
            print(f"  {price_entry['price_str']} ({price_entry['airline']})")

    save_tracked(tracked)

    print(f"\nNow tracking {added} new route(s).", end="")
    if skipped:
        print(f" ({skipped} already tracked)", end="")
    print()
    if args.target_price:
        print(f"Target price: {fmt_price(args.target_price, currency)}")


if __name__ == "__main__":
    main()
