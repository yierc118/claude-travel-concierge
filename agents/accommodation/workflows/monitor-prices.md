# Workflow: Monitor Accommodation Prices (Cron — every 12h)

## Purpose
Check tracked properties for price changes across all active trips.

## Steps

1. Read all `trips/*/skeleton.json` — collect trips where `status == "active"`
2. For each active trip, read `trips/[id]/accommodation.json`
3. For each property option in each city:
   - If hotelclaw is available: `python skills/hotelclaw/scripts/check-prices.py --threshold 5`
   - If not available: use web search to check current price, update manually
4. Append new price snapshot to `price_history` array
5. Update `last_checked` timestamp
6. If price dropped ≥15%, append alert to `trips/[id]/STATUS.md`
7. Log run to `output/changelog.md`

## Error Handling
- If a property URL is no longer available, flag in STATUS.md with ⚠️ "Property may no longer be available"
- Continue with remaining properties — do not fail the whole run
