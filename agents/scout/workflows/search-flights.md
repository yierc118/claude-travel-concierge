# Workflow: Search Flights (Phase 2)

## Purpose
Search all flight legs in the trip skeleton and write results to flights.json.

## Input
`trips/[trip-id]/skeleton.json` — read the `legs` array.

## Steps

For each leg in `skeleton.legs`:
1. Run FlightClaw search:
```bash
python skills/flightclaw/scripts/search-flights.py \
  [leg.from] [leg.to] [leg.date] \
  --results 5
```

2. Also run date range search (±3 days) to surface cheaper alternatives:
```bash
python skills/flightclaw/scripts/search-flights.py \
  [leg.from] [leg.to] [leg.date -3 days] \
  --date-to [leg.date +3 days] \
  --results 3
```

3. Add route to tracking:
```bash
python skills/flightclaw/scripts/track-flight.py \
  [leg.from] [leg.to] [leg.date]
```

4. Write results to `trips/[trip-id]/flights.json`:
```json
{
  "legs": [
    {
      "from": "SIN",
      "to": "NRT",
      "date": "2026-05-14",
      "cabin": "ECONOMY",
      "booked": false,
      "flight_number": null,
      "options": [
        {
          "price": 450,
          "currency": "USD",
          "airline": "SQ",
          "stops": 0,
          "duration_min": 390
        }
      ],
      "price_history": [
        { "timestamp": "2026-03-17T08:00:00+08:00", "price": 450, "currency": "USD" }
      ],
      "tracked_since": "2026-03-17",
      "last_checked": "2026-03-17T08:00:00+08:00"
    }
  ]
}
```

## Output
Write `trips/[trip-id]/flights.json`. Update STATUS.md: append "Scout: Phase 2 complete — [N] legs searched".
