#!/usr/bin/env python3
"""List all tracked properties."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers import load_tracked, fmt_price


def main():
    tracked = load_tracked()
    if not tracked:
        print("No properties being tracked.")
        sys.exit(0)

    for entry in tracked:
        currency = entry.get("currency", "USD")
        print(f"{entry['name']} | {entry['city']} | {entry['check_in']} → {entry['check_out']} ({entry['nights']} nights)")
        history = entry.get("price_history", [])
        if history:
            last = history[-1].get("price_per_night")
            if last:
                print(f"  Current: {fmt_price(last, currency)}/night | Checks: {len(history)}")
        if entry.get("target_price"):
            print(f"  Target: {fmt_price(entry['target_price'], currency)}/night")
        print(f"  ID: {entry['id']}")
        print()

    print(f"{len(tracked)} property(ies) tracked.")


if __name__ == "__main__":
    main()
