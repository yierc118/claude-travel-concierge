#!/usr/bin/env python3
"""Add a property to price tracking."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers import load_tracked, save_tracked, fmt_price
from scrapers import search_all_sources
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description="Track a hotel property")
    parser.add_argument("name", help="Property name")
    parser.add_argument("city", help="City name")
    parser.add_argument("check_in", help="Check-in date (YYYY-MM-DD)")
    parser.add_argument("check_out", help="Check-out date (YYYY-MM-DD)")
    parser.add_argument("--url", default="", help="Direct booking URL")
    parser.add_argument("--target-price", type=float, help="Alert threshold (USD/night)")
    args = parser.parse_args()

    tracked = load_tracked()
    property_id = f"{args.city.lower().replace(' ', '-')}-{args.name.lower().replace(' ', '-')}-{args.check_in}"

    if any(t["id"] == property_id for t in tracked):
        print(f"Already tracking: {args.name} in {args.city}")
        sys.exit(0)

    nights = (datetime.fromisoformat(args.check_out) - datetime.fromisoformat(args.check_in)).days
    now = datetime.now(timezone.utc).isoformat()

    print(f"Getting initial price for {args.name}...")
    initial_price = None
    try:
        results, _ = search_all_sources(args.city, args.check_in, args.check_out, results_per_source=3)
        match = next((r for r in results if args.name.lower() in r["name"].lower()), None)
        if match:
            initial_price = match["price_per_night"]
    except Exception as e:
        print(f"Could not get initial price: {e}")

    entry = {
        "id": property_id,
        "name": args.name,
        "city": args.city,
        "check_in": args.check_in,
        "check_out": args.check_out,
        "nights": nights,
        "url": args.url,
        "target_price": args.target_price,
        "currency": "USD",
        "added_at": now,
        "price_history": [{"timestamp": now, "price_per_night": initial_price}],
    }

    tracked.append(entry)
    save_tracked(tracked)

    price_msg = fmt_price(initial_price) + "/night" if initial_price else "price unknown"
    print(f"Now tracking: {args.name} in {args.city} ({args.check_in} → {args.check_out}, {nights} nights) — {price_msg}")


if __name__ == "__main__":
    main()
