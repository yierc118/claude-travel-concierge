# Workflow: Monitor Flight Prices (Cron — every 6h)

## Purpose
Check all tracked routes for price changes across all active trips.

## Steps

1. Read all `trips/*/skeleton.json` — collect trips where `status == "active"`
2. Run FlightClaw price check:
```bash
python skills/flightclaw/scripts/check-prices.py --threshold 5
```
3. For each active trip, read `trips/[id]/flights.json`
4. For each leg, run a fresh search and append to `price_history`:
```bash
python skills/flightclaw/scripts/search-flights.py [from] [to] [date] --results 1
```
5. Append new snapshot to `price_history` array in `flights.json`
6. Update `last_checked` timestamp
7. If any price dropped by ≥15% since last check, append to `trips/[id]/STATUS.md`:
   ```
   ALERT [datetime]: SIN→NRT dropped to $380 (Buy now — 18% below avg)
   ```
8. Log run to `output/changelog.md`:
   ```
   [datetime] Scout cron: checked [N] routes across [M] trips. Alerts: [count]
   ```

## Error Handling
- If FlightClaw returns no results for a leg, log to changelog.md with ⚠️ and continue — do not fail the whole run
- Update `last_checked` even on failure so stale detection works correctly
