#!/usr/bin/env python3
"""Search Google Flights for a route and date."""

import argparse
import sys
from datetime import datetime, timedelta
from itertools import product

from fast_flights import FlightData, Passengers, get_flights
from search_utils import parse_price_str

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


def parse_args():
    parser = argparse.ArgumentParser(description="Search Google Flights")
    parser.add_argument("origin", help="Origin airport IATA code(s), comma-separated (e.g. HKG or HKG,ZHH)")
    parser.add_argument("destination", help="Destination airport IATA code(s), comma-separated")
    parser.add_argument("date", help="Departure date (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="End of date range (YYYY-MM-DD). Searches each day from date to date-to.")
    parser.add_argument("--return-date", help="Return date for round trips (YYYY-MM-DD)")
    parser.add_argument("--cabin", default="ECONOMY", choices=SEAT_MAP.keys(), help="Cabin class")
    parser.add_argument("--stops", default="ANY", choices=STOPS_MAP.keys(), help="Max stops")
    parser.add_argument("--results", type=int, default=5, help="Number of results")
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
    total_results = 0

    for orig_code, dest_code, date in combos:
        print(f"\nSearching {orig_code} -> {dest_code} on {date}...")

        flight_data = [FlightData(date=date, from_airport=orig_code, to_airport=dest_code)]
        trip = "one-way"
        if args.return_date:
            flight_data.append(FlightData(date=args.return_date, from_airport=dest_code, to_airport=orig_code))
            trip = "round-trip"

        try:
            result = get_flights(
                flight_data=flight_data,
                trip=trip,
                passengers=Passengers(adults=args.adults),
                seat=SEAT_MAP[args.cabin],
                max_stops=STOPS_MAP[args.stops],
            )
        except Exception as e:
            print(f"Search failed: {e}", file=sys.stderr)
            continue

        flights = result.flights[:args.results]
        if not flights:
            print("No flights found.")
            continue

        print(f"Price trend: {result.current_price}")
        for i, flight in enumerate(flights, 1):
            ahead = f" (+{flight.arrival_time_ahead})" if flight.arrival_time_ahead else ""
            print(f"\n{'='*60}")
            print(f"Option {i}: {flight.price} | {flight.duration} | {flight.stops} stop(s)")
            print(f"  {flight.name}: departs {flight.departure} -> arrives {flight.arrival}{ahead}")
            if flight.delay:
                print(f"  Delay: {flight.delay}")

        print(f"\n{len(flights)} result(s) found.")
        total_results += len(flights)

    if len(combos) > 1:
        print(f"\n{'='*60}")
        print(f"Searched {len(combos)} route/date combination(s). {total_results} total result(s).")


if __name__ == "__main__":
    main()
