#!/usr/bin/env python3
"""Check prices for all tracked properties."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers import load_tracked, save_tracked, fmt_price
from scrapers import search_all_sources
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description="Check tracked property prices")
    parser.add_argument("--threshold", type=float, default=15.0, help="Alert threshold % (default 15)")
    args = parser.parse_args()

    tracked = load_tracked()
    if not tracked:
        print("No properties tracked. Use track-property.py to add one.")
        sys.exit(0)

    now = datetime.now(timezone.utc).isoformat()
    alerts = []

    for entry in tracked:
        label = f"{entry['name']} ({entry['city']}, {entry['check_in']})"
        try:
            results, warnings = search_all_sources(entry["name"], entry["check_in"], entry["check_out"], results_per_source=3)
            match = next((r for r in results if entry["name"].lower() in r["name"].lower()), None)
            price = match["price_per_night"] if match else None
        except Exception as e:
            print(f"{label}: Error — {e}")
            continue

        if price is None:
            print(f"{label}: No price found")
            continue

        entry["price_history"].append({"timestamp": now, "price_per_night": price})
        prev_prices = [p["price_per_night"] for p in entry["price_history"][:-1] if p["price_per_night"]]

        if prev_prices:
            last = prev_prices[-1]
            change = price - last
            pct = (change / last) * 100
            direction = "DOWN" if change < 0 else "up"
            print(f"{label}: {fmt_price(price)}/night ({direction} {abs(pct):.1f}%)")
            if change < 0 and abs(pct) >= args.threshold:
                alerts.append(f"PRICE DROP: {label} — now {fmt_price(price)}/night (was {fmt_price(last)}, down {abs(pct):.1f}%)")
        else:
            print(f"{label}: {fmt_price(price)}/night (first check)")

        if entry.get("target_price") and price <= entry["target_price"]:
            alerts.append(f"TARGET REACHED: {label} — {fmt_price(price)}/night")

    save_tracked(tracked)

    if alerts:
        print("\nALERTS:")
        for a in alerts:
            print(f"  {a}")


if __name__ == "__main__":
    main()
