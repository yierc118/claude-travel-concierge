---
name: hotelclaw
description: Track hotel and accommodation prices from Google Hotels, Booking.com, and Airbnb. Search by city and dates, track properties over time, and get alerts when prices drop. Mirrors flightclaw's interface. Requires Python 3.10+, playwright, and optionally serpapi for Google Hotels. Run setup.sh to install dependencies.
---

# hotelclaw

Track accommodation prices across Google Hotels, Booking.com, and Airbnb. Search options, monitor prices over time, and get alerts when prices drop.

## Install

```bash
bash skills/hotelclaw/setup.sh
```

## Scripts

### Search Hotels
```bash
python skills/hotelclaw/scripts/search-hotels.py "Tokyo" 2026-05-14 2026-05-18
python skills/hotelclaw/scripts/search-hotels.py "Tokyo" 2026-05-14 2026-05-18 --guests 2
python skills/hotelclaw/scripts/search-hotels.py "Tokyo" 2026-05-14 2026-05-18 --results 10
```

### Track a Property
```bash
python skills/hotelclaw/scripts/track-property.py "Shinjuku Granbell Hotel" "Tokyo" 2026-05-14 2026-05-18
python skills/hotelclaw/scripts/track-property.py "Shinjuku Granbell Hotel" "Tokyo" 2026-05-14 2026-05-18 --url "https://..."
```

### Check Prices
```bash
python skills/hotelclaw/scripts/check-prices.py
python skills/hotelclaw/scripts/check-prices.py --threshold 15
```

### List Tracked
```bash
python skills/hotelclaw/scripts/list-tracked.py
```
