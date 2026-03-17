# Workflow: Plan Trip (Phase 1 → 2 → 3)

## Purpose
Orchestrate a trip from initial concept through to a working itinerary draft.

## Phase 1 — Skeleton (Sequential, Interactive)

Ask the user the following, one at a time:
1. Where are you going? (destination cities in order)
2. What are your travel dates? (departure and return)
3. How many nights per city?
4. How many travellers?
5. What's your total budget (USD or local currency)?
6. Any hard constraints? (nonstop flights only, specific hotels, etc.)

Once all answers collected:
1. Generate trip ID: `[destination-slug]-[YYYY-MM]` (e.g. `japan-2026-05`)
2. Confirm trip ID with user
3. Create directory: `trips/[trip-id]/`
4. Write `trips/[trip-id]/skeleton.json`:

```json
{
  "trip_id": "japan-2026-05",
  "status": "active",
  "phase": "1-complete",
  "travellers": 1,
  "budget_usd": 3200,
  "cities": [
    { "name": "Tokyo", "country": "JP", "airport": "NRT", "nights": 4, "arrive": "2026-05-14", "depart": "2026-05-18" }
  ],
  "legs": [
    { "from": "SIN", "to": "NRT", "date": "2026-05-14", "type": "international" },
    { "from": "NRT", "to": "SIN", "date": "2026-05-21", "type": "international" }
  ],
  "constraints": [],
  "created": "2026-03-17"
}
```

5. Write `trips/[trip-id]/STATUS.md`:
```
# Status: japan-2026-05
Phase: 1-complete
Last updated: [date]
Pending: Phase 2 — parallel execution ready to launch
```

6. Write `trips/[trip-id]/budget.json`:
```json
{ "budget_usd": 3200, "items": [] }
```

7. Tell user: "Skeleton locked. Ready to launch parallel research — Scout will search flights, Accommodation will find hotels, and I'll draft daily activities. This runs in parallel. Launch now?"

## Phase 2 — Parallel Execution

When user confirms, dispatch three subagents in parallel (single message, three Agent tool calls):

1. **Scout Agent** — read `agents/scout/AGENT.md`, run `workflows/search-flights.md`, input: `trips/[trip-id]/skeleton.json`
2. **Accommodation Agent** — read `agents/accommodation/AGENT.md`, run `workflows/find-accommodation.md`, input: `trips/[trip-id]/skeleton.json`
3. **Self (activities)** — generate day-by-day activity suggestions for each city using skeleton dates. Write to `trips/[trip-id]/itinerary.md` as draft sections.

Update STATUS.md: `Phase: 2-running`

Wait for all three to complete. Update STATUS.md: `Phase: 2.5-checkpoint`

If a subagent fails or produces no output file (flights.json or accommodation.json missing or empty):
- Log the failure to `output/changelog.md` with ⚠️
- Continue Phase 2.5 with available data — do not block on partial failure
- Surface the failure to the user at Phase 2.5: "⚠️ [Scout/Accommodation] Agent failed — [reason if known]. Proceeding with available results."

## Phase 2.5 — Human Checkpoint

Surface results to user:
- "Flights found: [summary from flights.json]"
- "Hotels shortlisted: [summary from accommodation.json]"
- "Activity draft: [brief summary]"

Ask: "Review these results. When you're ready, say 'approve' or let me know what to change."

Do not proceed to Phase 3 until user explicitly approves.

## Phase 3 — Reconciliation

Read all Phase 2 outputs. Synthesise:
1. Check flight arrival times — adjust Day 1 activities to start after landing + transit (allow 2h after arrival)
2. Check hotel locations — cluster activities near each hotel's neighbourhood
3. Identify any conflicts (e.g. attraction closed on arrival day) and resolve
4. Update `itinerary.md` with reconciled, full draft
5. Add footer to itinerary.md:
   ```
   ---
   Agent last updated: [datetime]
   User last edited: —
   ```
6. Update STATUS.md: `Phase: 4-active`
7. Register crons (see Cron Setup below)

Tell user: "Itinerary draft complete. It's saved to trips/[trip-id]/itinerary.md — you can edit it directly or ask me to make changes."

## Cron Setup (run at end of Phase 3)

Before registering, run CronList to check if crons for this trip already exist (look for the trip ID in the cron description). If found, skip — do not register duplicates.

Register the following crons using Claude Code's CronCreate:
- Scout price check: `every 6 hours` → run `agents/scout/workflows/monitor-prices.md` for this trip
- Accommodation price check: `every 12 hours` → run `agents/accommodation/workflows/monitor-prices.md` for this trip
- Daily report: `daily at 08:00 Asia/Hong_Kong` → run `agents/trip-planner/workflows/budget-tracking.md` daily report
