# Workflow: Budget Tracking

## Purpose
Two uses: (1) daily 08:00 cron report, (2) on-demand budget check.

## Daily Report (Cron)

1. Read all `trips/*/skeleton.json` — collect all trips where `status == "active"`
2. For each active trip:
   a. Read `trips/[id]/flights.json` — get all tracked routes and latest prices
   b. Read `trips/[id]/accommodation.json` — get all tracked properties and latest prices
   c. Classify each item (Buy now / Good deal / Fair / Above avg / No data yet) using price history
   d. Read `trips/[id]/budget.json` — get committed spend and estimates
3. Compose email:
   - Subject: `✈️ Travel Price Report — [date]`
   - Body: one section per active trip, flights then accommodation, badge per item
   - Include ⚠️ for any stale prices (last snapshot >18h ago)
   - Include ⚠️ for any scraper failures logged in output/changelog.md since last report
4. Send via Gmail MCP
5. Write summary to each trip's STATUS.md under "Last Report"

## On-Demand Budget Check

1. Read `trips/[trip-id]/budget.json`
2. Compute: committed spend, estimated spend, remaining vs budget
3. Display summary:
   ```
   Budget:    $3,200
   Committed: $840  (flights confirmed)
   Estimated: $1,840 (all categories)
   Remaining: $1,360
   ```

## Budget Item Schema

Each item in `budget.json` items array follows this structure:
```json
{
  "category": "flight",       // one of: flight, accommodation, food, transport, activities, other
  "description": "SQ321 SIN→NRT",
  "amount": 487,              // numeric, USD
  "type": "confirmed",        // "confirmed" (booked) or "estimate" (projected)
  "added": "2026-03-17T08:00:00+00:00"  // ISO 8601 UTC timestamp
}
```

The `budget_ledger.py` tool enforces these types. Call `add_item(trip_dir, category, description, amount, type)` to write items.

## Price Classification Logic

```python
def classify_price(current, history):
    if len(history) < 3:
        return "no_data"
    avg = sum(h["price"] for h in history) / len(history)
    pct = (current - avg) / avg * 100
    if pct <= -15:
        return "buy_now"
    elif pct <= -5:
        return "good_deal"
    elif pct <= 5:
        return "fair"
    else:
        return "above_avg"
```

## Stale Data Check

A price snapshot is stale if the most recent snapshot timestamp is more than 18 hours ago. Flag with ⚠️ in both email and STATUS.md.
