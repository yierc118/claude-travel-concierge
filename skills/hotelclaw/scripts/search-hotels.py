#!/usr/bin/env python3
"""Search for hotels in a city for given dates."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers import search_all_sources
from helpers import fmt_price


def main():
    parser = argparse.ArgumentParser(description="Search hotel prices")
    parser.add_argument("city", help="City name (e.g. Tokyo)")
    parser.add_argument("check_in", help="Check-in date (YYYY-MM-DD)")
    parser.add_argument("check_out", help="Check-out date (YYYY-MM-DD)")
    parser.add_argument("--guests", type=int, default=1, help="Number of guests")
    parser.add_argument("--results", type=int, default=5, help="Max results per source")
    args = parser.parse_args()

    print(f"Searching accommodation in {args.city} ({args.check_in} → {args.check_out}, {args.guests} guest(s))...\n")

    options, warnings = search_all_sources(args.city, args.check_in, args.check_out, args.guests, args.results)

    if not options:
        print("No results found.")
        if warnings:
            print("\n".join(warnings))
        sys.exit(1)

    for opt in options:
        print(f"• {opt['name']} [{opt['source']}]")
        print(f"  {opt['area']} | {fmt_price(opt['price_per_night'])}/night | {opt.get('url', '')}")
        print()

    if warnings:
        print("\n".join(warnings))

    print(f"{len(options)} option(s) found.")


if __name__ == "__main__":
    main()
