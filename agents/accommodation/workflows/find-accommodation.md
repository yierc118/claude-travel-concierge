# Workflow: Find Accommodation (Phase 2)

## Purpose
Research accommodation options for each city in the trip and write shortlist to accommodation.json.

## Input
`trips/[trip-id]/skeleton.json` — read the `cities` array.

## Steps

For each city in `skeleton.cities`:
1. Search for 3–5 accommodation options:
   - Use web search: "[city] hotel [arrive date] [depart date] [travellers] people"
   - Target: mix of 1 budget, 2 mid-range, 1 splurge option
   - Note: once hotelclaw is built, replace this with `python skills/hotelclaw/scripts/search-hotels.py [city] [arrive] [depart]`

2. Write results to `trips/[trip-id]/accommodation.json`:
```json
{
  "cities": [
    {
      "city": "Tokyo",
      "arrive": "2026-05-14",
      "depart": "2026-05-18",
      "nights": 4,
      "options": [
        {
          "name": "Shinjuku Granbell Hotel",
          "type": "hotel",
          "area": "Shinjuku",
          "price_per_night": 120,
          "currency": "USD",
          "total_price": 480,
          "url": "https://...",
          "booked": false,
          "price_history": [
            { "timestamp": "2026-03-17T08:00:00+08:00", "price": 120, "currency": "USD" }
          ],
          "tracked_since": "2026-03-17",
          "last_checked": "2026-03-17T08:00:00+08:00"
        }
      ]
    }
  ]
}
```

## Error Handling
- **Web search fails for a city:** Log the failure to STATUS.md ("Accommodation search failed for [city] — skipping"), continue with remaining cities. Do not abort the whole run.
- **Fewer than 3 results found for a city:** Write what you have, note the shortage in STATUS.md. Do not fabricate options.
- **accommodation.json already exists:** Append new cities rather than overwriting. Do not remove existing entries.

## Output
Write `trips/[trip-id]/accommodation.json`. Update STATUS.md: append "Accommodation: Phase 2 complete — [N] options found across [M] cities. Skipped: [list any failed cities]".
