# hotelclaw

Track accommodation prices across Google Hotels, Booking.com, and Airbnb. Mirrors flightclaw's interface and data format.

## Install

```bash
bash skills/hotelclaw/setup.sh
```

## Sources

| Source | Tool | Requires |
|--------|------|----------|
| Google Hotels | SerpAPI | `SERPAPI_KEY` env var (optional) |
| Booking.com | Playwright headless | None |
| Airbnb | Playwright headless | None |

Each source fails independently — if one is blocked, the others continue.

## Usage

### Search
```bash
python skills/hotelclaw/scripts/search-hotels.py "Tokyo" 2026-05-14 2026-05-18
python skills/hotelclaw/scripts/search-hotels.py "Tokyo" 2026-05-14 2026-05-18 --guests 2
```

### Track
```bash
python skills/hotelclaw/scripts/track-property.py "Shinjuku Granbell Hotel" "Tokyo" 2026-05-14 2026-05-18
```

### Monitor prices
```bash
python skills/hotelclaw/scripts/check-prices.py --threshold 15
```

### List tracked
```bash
python skills/hotelclaw/scripts/list-tracked.py
```

## MCP Server

```bash
python skills/hotelclaw/server.py
```

## Data format

Properties are stored in `skills/hotelclaw/data/tracked.json`:

```json
[
  {
    "id": "tokyo-shinjuku-granbell-hotel-2026-05-14",
    "name": "Shinjuku Granbell Hotel",
    "city": "Tokyo",
    "check_in": "2026-05-14",
    "check_out": "2026-05-18",
    "nights": 4,
    "url": "https://...",
    "target_price": 100,
    "currency": "USD",
    "added_at": "2026-03-17T00:00:00+00:00",
    "price_history": [
      { "timestamp": "2026-03-17T00:00:00+00:00", "price_per_night": 120 }
    ]
  }
]
```
