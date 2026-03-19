#!/usr/bin/env python3
"""Check all tracked flights for price changes. Designed for cron/scheduled use."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

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
    if not os.path.exists(TRACKED_FILE):
        return []
    with open(TRACKED_FILE, "r") as f:
        return json.load(f)


def save_tracked(tracked):
    with open(TRACKED_FILE, "w") as f:
        json.dump(tracked, f, indent=2)


def parse_args():
    parser = argparse.ArgumentParser(description="Check tracked flight prices")
    parser.add_argument("--threshold", type=float, default=10, help="Percentage drop to alert on (default: 10)")
    return parser.parse_args()


def check_route(entry):
    flight_data = [FlightData(date=entry["date"], from_airport=entry["origin"], to_airport=entry["destination"])]
    trip = "one-way"
    if entry.get("return_date"):
        flight_data.append(FlightData(date=entry["return_date"], from_airport=entry["destination"], to_airport=entry["origin"]))
        trip = "round-trip"

    result = get_flights(
        flight_data=flight_data,
        trip=trip,
        passengers=Passengers(adults=1),
        seat=SEAT_MAP.get(entry.get("cabin", "ECONOMY"), "economy"),
        max_stops=STOPS_MAP.get(entry.get("stops", "ANY")),
    )

    if not result.flights:
        return None, None, None

    best = result.flights[0]
    return parse_price_str(best.price), best.name, best.price


def main():
    args = parse_args()
    tracked = load_tracked()

    if not tracked:
        print("No flights being tracked. Use track-flight.py to add routes.")
        sys.exit(0)

    now = datetime.now(timezone.utc).isoformat()
    alerts = []

    for entry in tracked:
        route = f"{entry['origin']} -> {entry['destination']} on {entry['date']}"
        print(f"Checking {route}...")

        try:
            price, airline, price_str = check_route(entry)
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            continue

        if price is None:
            print("  No results found")
            continue

        entry["price_history"].append({
            "timestamp": now,
            "best_price": price,
            "airline": airline,
            "price_str": price_str,
        })

        prev_prices = [p["best_price"] for p in entry["price_history"][:-1] if p.get("best_price")]
        if prev_prices:
            last_price = prev_prices[-1]
            change = price - last_price
            pct = (change / last_price) * 100

            if change < 0:
                print(f"  {price_str} ({airline}) - DOWN {abs(pct):.1f}%")
                if abs(pct) >= args.threshold:
                    alerts.append(f"PRICE DROP: {route} is now {price_str} (was {last_price:.0f}, down {abs(pct):.1f}%)")
            elif change > 0:
                print(f"  {price_str} ({airline}) - up {pct:.1f}%")
            else:
                print(f"  {price_str} ({airline}) - no change")
        else:
            print(f"  {price_str} ({airline}) - first price recorded")

        if entry.get("target_price") and price <= entry["target_price"]:
            alerts.append(f"TARGET REACHED: {route} is {price_str} (target: {entry['target_price']:.0f})")

    save_tracked(tracked)

    if alerts:
        print(f"\n{'='*60}")
        print("ALERTS:")
        for alert in alerts:
            print(f"  {alert}")


if __name__ == "__main__":
    main()
