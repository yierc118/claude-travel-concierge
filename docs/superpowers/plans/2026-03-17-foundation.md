# Travel Concierge — Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the full BITT project structure, implement all agent identity files and workflows, build the Python tools layer (AirLabs, budget ledger, calendar sync), wire in FlightClaw, register crons, and set up slash commands — producing a working multi-agent travel concierge system without the dashboard or hotelclaw skill.

**Architecture:** Four BITT agents (Trip Planner, Scout, Accommodation, Booking) communicate through shared JSON state files in `/trips/[trip-id]/`. The Trip Planner is the parent coordinator; subagents are dispatched in parallel during Phase 2. Crons run Scout and Accommodation Agents on schedule via Claude Code's native CronCreate. Python tools handle all external API calls and file I/O.

**Tech Stack:** Python 3.11+ (tools + scripts), FlightClaw skill (existing, Google Flights via `fli`), AirLabs REST API, Google Calendar MCP, Gmail MCP, Claude Code native crons and parallel agents.

---

## File Map

### Created by this plan

```
MEMORY.md                                      (update Project Identity)
.env.example                                   (document all required keys)
.gitignore                                     (add standard ignores)

/agents/trip-planner/AGENT.md
/agents/trip-planner/workflows/plan-trip.md
/agents/trip-planner/workflows/update-itinerary.md
/agents/trip-planner/workflows/budget-tracking.md

/agents/scout/AGENT.md
/agents/scout/workflows/search-flights.md
/agents/scout/workflows/monitor-prices.md
/agents/scout/workflows/track-departure.md

/agents/accommodation/AGENT.md
/agents/accommodation/workflows/find-accommodation.md
/agents/accommodation/workflows/monitor-prices.md

/agents/booking/AGENT.md
/agents/booking/workflows/book-and-confirm.md

/tools/airlabs.py                              (AirLabs API wrapper)
/tools/budget_ledger.py                        (read/write budget.json)
/tools/calendar_sync.py                        (Google Calendar MCP helper)
/tools/__init__.py

/tests/test_airlabs.py
/tests/test_budget_ledger.py
/tests/test_calendar_sync.py

/skills/flightclaw/                            (copied from /reference/flightclaw/)

/trips/.gitkeep                                (empty dir placeholder)

/.claude/commands/plan-trip.md
/.claude/commands/check-flights.md
/.claude/commands/find-hotels.md
/.claude/commands/check-budget.md
/.claude/commands/dashboard.md
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `.env.example`
- Create: `.gitignore`
- Update: `MEMORY.md`
- Create: `trips/.gitkeep`
- Create: `tools/__init__.py`

- [ ] **Step 1: Create `.env.example`**

```
# AirLabs API — flight departure monitoring (day-of tracking for booked flights)
# Get key at: https://airlabs.co
AIRLABS_API_KEY=your_key_here

# SerpAPI — optional, for hotelclaw Google Hotels scraping
# Get key at: https://serpapi.com (free tier: 100 searches/month)
# Leave blank to skip Google Hotels source in hotelclaw
SERPAPI_KEY=

# Dashboard server port (default: 8000)
DASHBOARD_PORT=8000
```

- [ ] **Step 2: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
.DS_Store
node_modules/
.tmp/
.superpowers/
trips/*/
!trips/.gitkeep
```

Note: `trips/*/` is gitignored because trip data is personal and contains PII. Only the placeholder is committed.

- [ ] **Step 3: Update `MEMORY.md` Project Identity section**

Replace the empty Project Identity block with:

```markdown
## Project Identity

> **Role:** You are a multi-agent travel concierge. You help plan, monitor, and execute trips through a team of specialised subagents.
>
> **Context:** This is both a personal travel planning tool and a showcase of Claude Code's agentic capabilities — parallel agents, cron schedules, and loops. Built on the BITT framework. The user is a non-technical builder (vibe coder) who understands architecture and product but is not writing code from scratch.
>
> **Voice & Style:** Direct, actionable, low-fluff. Surface decisions clearly. Never auto-book or auto-pay — always pause for approval. Ask clarifying questions before starting Phase 1.
>
> **Output:** Trip state files in `/trips/[trip-id]/`, itinerary as `itinerary.md`, daily email reports via Gmail MCP.
```

- [ ] **Step 4: Create directory structure**

```bash
mkdir -p "agents/trip-planner/workflows"
mkdir -p "agents/scout/workflows"
mkdir -p "agents/accommodation/workflows"
mkdir -p "agents/booking/workflows"
mkdir -p tools
mkdir -p tests
mkdir -p trips
mkdir -p "skills/flightclaw"
touch trips/.gitkeep
touch tools/__init__.py
```

- [ ] **Step 5: Copy FlightClaw from reference**

```bash
cp -r "reference/flightclaw/." "skills/flightclaw/"
```

Verify it copied correctly:
```bash
ls skills/flightclaw/
# Expected: setup.sh  server.py  README.md  .gitignore  scripts  SKILL.md  tracking.py  data  helpers.py
```

- [ ] **Step 6: Install FlightClaw dependencies**

```bash
cd skills/flightclaw && bash setup.sh
```

If `setup.sh` fails, run manually:
```bash
pip install flights "mcp[cli]"
```

- [ ] **Step 7: Commit scaffold**

```bash
git init  # if not already a git repo
git add .env.example .gitignore MEMORY.md trips/.gitkeep tools/__init__.py
git add skills/flightclaw/
git commit -m "feat: scaffold project structure and copy flightclaw skill"
```

---

## Task 2: Trip Planner Agent Files

**Files:**
- Create: `agents/trip-planner/AGENT.md`
- Create: `agents/trip-planner/workflows/plan-trip.md`
- Create: `agents/trip-planner/workflows/update-itinerary.md`
- Create: `agents/trip-planner/workflows/budget-tracking.md`

- [ ] **Step 1: Create `agents/trip-planner/AGENT.md`**

```markdown
# Trip Planner Agent

You are the parent coordinator for the Travel Concierge system. You are the only agent that talks to the user directly. All subagents report back to you.

## Identity

**Role:** Parent coordinator — plan trips, route tasks to subagents, maintain itineraries, track budgets.

**Scope:**
- IN: Phase 1–4 orchestration, itinerary building and editing, budget ledger, daily reports, calendar sync, dispatching Scout/Accommodation/Booking agents
- OUT: Direct flight searches (delegate to Scout), direct hotel searches (delegate to Accommodation), executing bookings (delegate to Booking)

**Voice & Style:** Direct and actionable. Ask one clarifying question at a time. Never assume — confirm trip details before writing skeleton.json.

**Constraints:**
- Never create new workflow files without user confirmation
- Never auto-pay or auto-book — Booking Agent always pauses for approval
- Always read the current `itinerary.md` before any reasoning in Phase 4
- Log all system changes to `/output/changelog.md`
- Check `trips/[trip-id]/STATUS.md` phase before acting — don't re-run completed phases

## Memory / Reference Files
- `MEMORY.md` — project identity and learned preferences
- `CLAUDE.md` — BITT operating instructions
- `trips/[trip-id]/STATUS.md` — current phase and pending actions
- `trips/[trip-id]/skeleton.json` — trip structure (cities, dates, legs)
- `trips/[trip-id]/itinerary.md` — living itinerary document

## Workflows
- `workflows/plan-trip.md` — Phase 1→2→3 orchestration
- `workflows/update-itinerary.md` — ongoing itinerary editing
- `workflows/budget-tracking.md` — budget ledger management
```

- [ ] **Step 2: Create `agents/trip-planner/workflows/plan-trip.md`**

```markdown
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
```

- [ ] **Step 3: Create `agents/trip-planner/workflows/update-itinerary.md`**

```markdown
# Workflow: Update Itinerary

## Purpose
Edit the living itinerary document in response to user requests or new information (e.g. a flight time changed, a restaurant closed).

## Steps

1. Read current `trips/[trip-id]/itinerary.md`
2. Read current `trips/[trip-id]/skeleton.json` (for dates and constraints)
3. Understand the requested change
4. Make the edit — preserve all existing sections not being changed
5. Update the footer:
   ```
   Agent last updated: [datetime]
   ```
6. Confirm the change to the user with a brief summary of what changed

## Rules
- Never overwrite the full file — edit the relevant section only
- If the user's edit conflicts with a booking (e.g. they move a day but a hotel is booked), flag the conflict before making the change
- If unsure what the user wants changed, ask before editing
```

- [ ] **Step 4: Create `agents/trip-planner/workflows/budget-tracking.md`**

```markdown
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
```

- [ ] **Step 5: Commit agent files**

```bash
git add agents/trip-planner/
git commit -m "feat: add trip-planner agent files and workflows"
```

---

## Task 3: Scout Agent Files

**Files:**
- Create: `agents/scout/AGENT.md`
- Create: `agents/scout/workflows/search-flights.md`
- Create: `agents/scout/workflows/monitor-prices.md`
- Create: `agents/scout/workflows/track-departure.md`

- [ ] **Step 1: Create `agents/scout/AGENT.md`**

```markdown
# Scout Agent

You are the flight specialist. You search for flights, track prices, and monitor booked flights on departure day.

## Identity

**Role:** Flight search, price tracking, and departure monitoring.

**Scope:**
- IN: Searching Google Flights via FlightClaw, tracking routes, checking prices, AirLabs departure status
- OUT: Hotel search (Accommodation Agent), booking execution (Booking Agent), itinerary editing

**Constraints:**
- Always use FlightClaw scripts for price data — never hallucinate prices
- AirLabs calls cost API credits — only call when a flight is booked AND departure is within 24h
- Write all results to `trips/[trip-id]/flights.json` — never output to the user directly when running as subagent

## Tools
- `skills/flightclaw/scripts/search-flights.py` — search routes
- `skills/flightclaw/scripts/track-flight.py` — add to tracking
- `skills/flightclaw/scripts/check-prices.py` — check all tracked
- `skills/flightclaw/scripts/list-tracked.py` — list tracked routes
- `tools/airlabs.py` — departure status for booked flights

## Memory / Reference Files
- `trips/[trip-id]/skeleton.json` — flight legs to search
- `trips/[trip-id]/flights.json` — output file
```

- [ ] **Step 2: Create `agents/scout/workflows/search-flights.md`**

```markdown
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
```

- [ ] **Step 3: Create `agents/scout/workflows/monitor-prices.md`**

```markdown
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
```

- [ ] **Step 4: Create `agents/scout/workflows/track-departure.md`**

```markdown
# Workflow: Track Departure (Cron — every 2h, day-of only)

## Purpose
Monitor booked flights on the day of travel using AirLabs API.

## Activation
This workflow only runs when: a flight entry in `flights.json` has `"booked": true` AND departure date is today.

## Steps

1. Read all `trips/*/flights.json`
2. For each leg where `booked == true`:
   a. Check if `date` == today (Asia/Hong_Kong timezone)
   b. If yes, call AirLabs:
   ```python
   # tools/airlabs.py
   status = get_flight_status(flight_number="SQ321", date="2026-05-14")
   ```
3. Write status to `trips/[id]/STATUS.md`:
   ```
   DEPARTURE [datetime]: SQ321 SIN→NRT — On time, departs 09:45 Gate B12
   ```
   Or if delayed:
   ```
   DEPARTURE ALERT [datetime]: SQ321 delayed. New departure: 11:20 (+95 min). Gate B14.
   ```
4. If delayed by >60 min, compose a Gmail draft (do not auto-send) via Gmail MCP with the delay info

## Notes
- Only runs day-of — the cron is registered with a condition check at the start
- AirLabs costs credits — check `booked == true` before every call
```

- [ ] **Step 5: Commit Scout files**

```bash
git add agents/scout/
git commit -m "feat: add scout agent files and workflows"
```

---

## Task 4: Accommodation Agent Files

**Files:**
- Create: `agents/accommodation/AGENT.md`
- Create: `agents/accommodation/workflows/find-accommodation.md`
- Create: `agents/accommodation/workflows/monitor-prices.md`

- [ ] **Step 1: Create `agents/accommodation/AGENT.md`**

```markdown
# Accommodation Agent

You research and track hotels, Airbnb, and short-term rentals for each city in a trip.

## Identity

**Role:** Accommodation research and price tracking.

**Scope:**
- IN: Searching and tracking accommodation options per city, maintaining shortlists, price monitoring
- OUT: Flight search (Scout), booking execution (Booking Agent), itinerary editing

**Constraints:**
- hotelclaw is not yet built — for now, use web search tool to find options and record them manually in accommodation.json
- Once hotelclaw is available, replace manual search with hotelclaw scripts
- Write all results to `trips/[trip-id]/accommodation.json` — never output directly to user when running as subagent

## Tools
- Web search (current fallback until hotelclaw is built)
- `skills/hotelclaw/` (future — Plan 2)

## Memory / Reference Files
- `trips/[trip-id]/skeleton.json` — cities and date ranges
- `trips/[trip-id]/accommodation.json` — output file
```

- [ ] **Step 2: Create `agents/accommodation/workflows/find-accommodation.md`**

```markdown
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

## Output
Write `trips/[trip-id]/accommodation.json`. Update STATUS.md: append "Accommodation: Phase 2 complete — [N] options found across [M] cities".
```

- [ ] **Step 3: Create `agents/accommodation/workflows/monitor-prices.md`**

```markdown
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
```

- [ ] **Step 4: Commit Accommodation files**

```bash
git add agents/accommodation/
git commit -m "feat: add accommodation agent files and workflows"
```

---

## Task 5: Booking Agent Files

**Files:**
- Create: `agents/booking/AGENT.md`
- Create: `agents/booking/workflows/book-and-confirm.md`

- [ ] **Step 1: Create `agents/booking/AGENT.md`**

```markdown
# Booking Agent

You execute assisted bookings: fill forms, navigate to the confirmation page, then pause for user approval before any payment.

## Identity

**Role:** Assisted booking for flights and accommodation.

**Scope:**
- IN: Navigating booking flows, filling passenger/guest details, reaching confirmation page, drafting confirmation emails
- OUT: Completing payments (always requires user), price research (Scout/Accommodation), itinerary editing

**Hard constraint:** NEVER complete a payment. Always stop at the confirmation/payment page and wait for explicit user approval. This is non-negotiable.

**Constraints:**
- Use browser automation tools (computer use / web browser) to navigate booking sites
- Credentials and payment details are entered by the user — never request or store them
- After a booking is confirmed by the user, write to budget.json and flights.json/accommodation.json
- Draft a confirmation email via Gmail MCP but do not send without user instruction

## Tools
- Browser / computer use tool for form navigation
- Gmail MCP for confirmation drafts
- `tools/budget_ledger.py` for updating budget after confirmed booking

## Memory / Reference Files
- `trips/[trip-id]/flights.json` or `accommodation.json` — item being booked
- `trips/[trip-id]/budget.json` — update after confirmation
```

- [ ] **Step 2: Create `agents/booking/workflows/book-and-confirm.md`**

```markdown
# Workflow: Book and Confirm

## Purpose
Navigate a booking flow for a specific flight or accommodation option, stop before payment, and await user approval.

## Input
User specifies: trip ID + what to book (e.g. "book the Shinjuku Granbell for Japan trip" or "book SIN→NRT on SQ on 14 May").

## Steps

### For Flights
1. Read `trips/[trip-id]/flights.json` — find the relevant leg and selected option
2. Open Google Flights or airline direct site in browser
3. Navigate to the specific flight
4. Fill in passenger details (ask user for name, passport, DOB if not provided)
5. Navigate to final confirmation/payment page
6. **STOP HERE** — display the booking summary to the user:
   ```
   Ready to book:
   SQ321  SIN → NRT  14 May 2026
   Passenger: [name]
   Price: $487 USD

   Please review and complete payment yourself. Let me know when done.
   ```
7. Wait for user to confirm they completed the booking
8. Ask user for: confirmation number, final price paid
9. Update `trips/[trip-id]/flights.json`:
   - Set `"booked": true`
   - Set `"flight_number": "SQ321"`
   - Set `"confirmed_price": 487`
10. Call `tools/budget_ledger.py` to add to budget.json:
    ```python
    add_item(trip_id, "flight", "SQ321 SIN→NRT", 487, "confirmed")
    ```
11. Draft confirmation email via Gmail MCP:
    - Subject: "Flight Confirmed: SQ321 SIN→NRT 14 May 2026"
    - Include: confirmation number, passenger, price, check-in link
12. Add to Google Calendar via Google Calendar MCP:
    - Event: "✈️ SIN → NRT (SQ321)"
    - Date/time: departure datetime
    - Description: flight details

### For Accommodation
Same pattern — navigate to booking site, fill guest details, STOP at payment, wait for user confirmation, then update accommodation.json and budget.json.

## Notes
- If the booking flow requires account login, ask user to log in first
- If the site blocks automated navigation, describe the steps to the user manually instead
```

- [ ] **Step 3: Commit Booking files**

```bash
git add agents/booking/
git commit -m "feat: add booking agent files and workflows"
```

---

## Task 6: Python Tools Layer

**Files:**
- Create: `tools/airlabs.py`
- Create: `tools/budget_ledger.py`
- Create: `tools/calendar_sync.py`
- Create: `tests/test_airlabs.py`
- Create: `tests/test_budget_ledger.py`
- Create: `tests/test_calendar_sync.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write failing tests for `budget_ledger.py`**

Create `tests/conftest.py`:
```python
import pytest
import json
import os
import tempfile

@pytest.fixture
def tmp_trip_dir(tmp_path):
    """Create a temporary trip directory with a budget.json."""
    trip_dir = tmp_path / "test-trip-2026-05"
    trip_dir.mkdir()
    budget = {
        "budget_usd": 3200,
        "items": []
    }
    (trip_dir / "budget.json").write_text(json.dumps(budget))
    return str(trip_dir)
```

Create `tests/test_budget_ledger.py`:
```python
import pytest
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.budget_ledger import add_item, get_summary, ITEM_TYPES


def test_add_confirmed_item(tmp_trip_dir):
    add_item(tmp_trip_dir, "flight", "SQ321 SIN→NRT", 487, "confirmed")
    with open(os.path.join(tmp_trip_dir, "budget.json")) as f:
        data = json.load(f)
    assert len(data["items"]) == 1
    assert data["items"][0]["amount"] == 487
    assert data["items"][0]["type"] == "confirmed"


def test_add_estimate_item(tmp_trip_dir):
    add_item(tmp_trip_dir, "food", "Daily food budget", 50, "estimate")
    with open(os.path.join(tmp_trip_dir, "budget.json")) as f:
        data = json.load(f)
    assert data["items"][0]["type"] == "estimate"


def test_summary_separates_confirmed_from_estimates(tmp_trip_dir):
    add_item(tmp_trip_dir, "flight", "SQ321", 487, "confirmed")
    add_item(tmp_trip_dir, "food", "Food", 400, "estimate")
    summary = get_summary(tmp_trip_dir)
    assert summary["budget_usd"] == 3200
    assert summary["committed"] == 487
    assert summary["estimated_total"] == 887
    assert summary["remaining"] == 3200 - 887


def test_invalid_item_type_raises(tmp_trip_dir):
    with pytest.raises(ValueError, match="Invalid category"):
        add_item(tmp_trip_dir, "invalid_category", "Test", 100, "confirmed")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge"
python -m pytest tests/test_budget_ledger.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.budget_ledger'`

- [ ] **Step 3: Implement `tools/budget_ledger.py`**

```python
"""
Budget ledger — read/write budget.json for a trip.
"""
import json
import os
from datetime import datetime, timezone

ITEM_TYPES = {"flight", "accommodation", "food", "transport", "activities", "other"}


def _read(trip_dir: str) -> dict:
    path = os.path.join(trip_dir, "budget.json")
    with open(path) as f:
        return json.load(f)


def _write(trip_dir: str, data: dict) -> None:
    path = os.path.join(trip_dir, "budget.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def add_item(trip_dir: str, category: str, description: str, amount: float, item_type: str) -> None:
    """
    Add a budget item.
    category: one of ITEM_TYPES
    item_type: 'confirmed' | 'estimate'
    """
    if category not in ITEM_TYPES:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {ITEM_TYPES}")
    if item_type not in ("confirmed", "estimate"):
        raise ValueError(f"Invalid item_type '{item_type}'. Must be 'confirmed' or 'estimate'.")

    data = _read(trip_dir)
    data["items"].append({
        "category": category,
        "description": description,
        "amount": amount,
        "type": item_type,
        "added": datetime.now(timezone.utc).isoformat(),
    })
    _write(trip_dir, data)


def get_summary(trip_dir: str) -> dict:
    """Return budget summary: committed, estimated_total, remaining."""
    data = _read(trip_dir)
    committed = sum(i["amount"] for i in data["items"] if i["type"] == "confirmed")
    estimated_total = sum(i["amount"] for i in data["items"])
    return {
        "budget_usd": data["budget_usd"],
        "committed": committed,
        "estimated_total": estimated_total,
        "remaining": data["budget_usd"] - estimated_total,
        "items": data["items"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_budget_ledger.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Write failing tests for `airlabs.py`**

Create `tests/test_airlabs.py`:
```python
import pytest
import os
import sys
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.airlabs import get_flight_status, AirLabsError


def test_get_flight_status_returns_structured_data():
    mock_response = {
        "response": {
            "flight_iata": "SQ321",
            "status": "en-route",
            "dep_time": "09:45",
            "arr_time": "17:30",
            "delayed": 0,
            "dep_terminal": "3",
            "dep_gate": "B12",
        }
    }
    with patch("tools.airlabs.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_response
        )
        result = get_flight_status("SQ321", "2026-05-14")

    assert result["flight_number"] == "SQ321"
    assert result["status"] == "en-route"
    assert result["delayed_minutes"] == 0
    assert result["gate"] == "B12"


def test_get_flight_status_raises_on_api_error():
    with patch("tools.airlabs.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=401,
            json=lambda: {"error": {"message": "Invalid API key"}}
        )
        with pytest.raises(AirLabsError, match="AirLabs API error"):
            get_flight_status("SQ321", "2026-05-14")


def test_get_flight_status_raises_if_no_api_key(monkeypatch):
    monkeypatch.delenv("AIRLABS_API_KEY", raising=False)
    with pytest.raises(AirLabsError, match="AIRLABS_API_KEY"):
        get_flight_status("SQ321", "2026-05-14")
```

- [ ] **Step 6: Run tests to verify they fail**

```bash
python -m pytest tests/test_airlabs.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.airlabs'`

- [ ] **Step 7: Implement `tools/airlabs.py`**

```python
"""
AirLabs API wrapper — flight departure status for booked flights.
Only called day-of for booked flights (costs API credits).
API docs: https://airlabs.co/docs/flight
"""
import os
import requests
from typing import Any


class AirLabsError(Exception):
    pass


def get_flight_status(flight_number: str, date: str) -> dict[str, Any]:
    """
    Get real-time status for a booked flight.

    Args:
        flight_number: IATA flight code, e.g. "SQ321"
        date: departure date in YYYY-MM-DD format

    Returns:
        dict with keys: flight_number, status, dep_time, arr_time,
                        delayed_minutes, terminal, gate
    """
    api_key = os.environ.get("AIRLABS_API_KEY")
    if not api_key:
        raise AirLabsError("AIRLABS_API_KEY environment variable is not set.")

    url = "https://airlabs.co/api/v9/flight"
    params = {"flight_iata": flight_number, "api_key": api_key}

    response = requests.get(url, params=params, timeout=10)

    if response.status_code != 200:
        raise AirLabsError(f"AirLabs API error {response.status_code}: {response.json()}")

    data = response.json().get("response", {})

    return {
        "flight_number": data.get("flight_iata", flight_number),
        "status": data.get("status", "unknown"),
        "dep_time": data.get("dep_time"),
        "arr_time": data.get("arr_time"),
        "delayed_minutes": data.get("delayed", 0) or 0,
        "terminal": data.get("dep_terminal"),
        "gate": data.get("dep_gate"),
    }
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
python -m pytest tests/test_airlabs.py -v
```

Expected: 3 tests PASS

- [ ] **Step 9: Write failing tests for `calendar_sync.py`**

Create `tests/test_calendar_sync.py`:
```python
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.calendar_sync import build_flight_event, build_hotel_event


def test_build_flight_event_returns_correct_structure():
    event = build_flight_event(
        flight_number="SQ321",
        origin="SIN",
        destination="NRT",
        departure_datetime="2026-05-14T09:45:00+08:00",
        arrival_datetime="2026-05-14T17:30:00+09:00",
        confirmation="ABC123"
    )
    assert event["summary"] == "✈️ SIN → NRT (SQ321)"
    assert event["start"]["dateTime"] == "2026-05-14T09:45:00+08:00"
    assert event["end"]["dateTime"] == "2026-05-14T17:30:00+09:00"
    assert "ABC123" in event["description"]


def test_build_hotel_event_returns_correct_structure():
    event = build_hotel_event(
        hotel_name="Shinjuku Granbell",
        city="Tokyo",
        check_in="2026-05-14",
        check_out="2026-05-18",
        confirmation="XYZ789"
    )
    assert event["summary"] == "🏨 Shinjuku Granbell (Tokyo)"
    assert event["start"]["date"] == "2026-05-14"
    assert event["end"]["date"] == "2026-05-18"
    assert "XYZ789" in event["description"]
```

- [ ] **Step 10: Run tests to verify they fail**

```bash
python -m pytest tests/test_calendar_sync.py -v
```

Expected: `ModuleNotFoundError: No module named 'tools.calendar_sync'`

- [ ] **Step 11: Implement `tools/calendar_sync.py`**

```python
"""
Google Calendar helpers — builds event dicts for use with Google Calendar MCP.
The actual MCP call is made by the agent; this module builds the payload.
"""
from typing import Any


def build_flight_event(
    flight_number: str,
    origin: str,
    destination: str,
    departure_datetime: str,
    arrival_datetime: str,
    confirmation: str = "",
) -> dict[str, Any]:
    """Build a Google Calendar event dict for a flight."""
    description = f"Flight: {flight_number}\nRoute: {origin} → {destination}"
    if confirmation:
        description += f"\nConfirmation: {confirmation}"

    return {
        "summary": f"✈️ {origin} → {destination} ({flight_number})",
        "start": {"dateTime": departure_datetime},
        "end": {"dateTime": arrival_datetime},
        "description": description,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 1440},  # 24h before
                {"method": "popup", "minutes": 180},   # 3h before
            ],
        },
    }


def build_hotel_event(
    hotel_name: str,
    city: str,
    check_in: str,
    check_out: str,
    confirmation: str = "",
) -> dict[str, Any]:
    """Build a Google Calendar event dict for a hotel stay (all-day)."""
    description = f"Hotel: {hotel_name}\nCity: {city}"
    if confirmation:
        description += f"\nConfirmation: {confirmation}"

    return {
        "summary": f"🏨 {hotel_name} ({city})",
        "start": {"date": check_in},
        "end": {"date": check_out},
        "description": description,
    }
```

- [ ] **Step 12: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 13: Commit tools and tests**

```bash
git add tools/ tests/
git commit -m "feat: add python tools layer (airlabs, budget_ledger, calendar_sync) with tests"
```

---

## Task 7: Slash Commands

**Files:**
- Create: `.claude/commands/plan-trip.md`
- Create: `.claude/commands/check-flights.md`
- Create: `.claude/commands/find-hotels.md`
- Create: `.claude/commands/check-budget.md`
- Create: `.claude/commands/dashboard.md`

- [ ] **Step 1: Create slash command files**

`.claude/commands/plan-trip.md`:
```markdown
Read agents/trip-planner/AGENT.md and agents/trip-planner/workflows/plan-trip.md. Start Phase 1 of a new trip plan. Ask the user for trip details one question at a time. Arguments (if provided): $ARGUMENTS
```

`.claude/commands/check-flights.md`:
```markdown
Read agents/scout/AGENT.md and agents/scout/workflows/search-flights.md. Search for flights or check tracked prices. If the user provides a route and date (e.g. "SIN NRT 2026-05-14"), search that route and offer to track it. If no arguments, show all currently tracked routes with latest prices. Arguments: $ARGUMENTS
```

`.claude/commands/find-hotels.md`:
```markdown
Read agents/accommodation/AGENT.md and agents/accommodation/workflows/find-accommodation.md. Search for accommodation options. Arguments should include: city, check-in date, check-out date, number of guests. Example: "Tokyo 2026-05-14 2026-05-18 1". Arguments: $ARGUMENTS
```

`.claude/commands/check-budget.md`:
```markdown
Read agents/trip-planner/AGENT.md and agents/trip-planner/workflows/budget-tracking.md. Show budget summary for the specified trip. If no trip ID is provided, list all active trips and their budget status. Arguments (trip ID): $ARGUMENTS
```

`.claude/commands/dashboard.md`:
```markdown
Launch the travel concierge dashboard server. Run: python tools/dashboard_server.py (Note: dashboard_server.py is built in Plan 3. If it does not exist yet, inform the user that the dashboard is not yet built.) Then open http://localhost:8000 in the browser.
```

- [ ] **Step 2: Verify slash commands are discoverable**

```bash
ls .claude/commands/
# Expected: check-budget.md  check-flights.md  dashboard.md  find-hotels.md  plan-trip.md
```

- [ ] **Step 3: Commit slash commands**

```bash
git add .claude/commands/
git commit -m "feat: add slash commands for plan-trip, check-flights, find-hotels, check-budget, dashboard"
```

---

## Task 8: Output Directory + Changelog

**Files:**
- Create: `output/changelog.md`

- [ ] **Step 1: Create `output/changelog.md`**

```markdown
# Changelog

Agent-maintained. Each automated run appends a brief entry.

---

## 2026-03-17
- Project scaffolded. Foundation plan implemented.
```

- [ ] **Step 2: Commit**

```bash
git add output/changelog.md
git commit -m "feat: add output directory and changelog"
```

---

## Task 9: End-to-End Smoke Test

Verify the full foundation works together without errors.

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 2: Verify FlightClaw works**

```bash
python skills/flightclaw/scripts/search-flights.py SIN NRT 2026-05-14 --results 3
```

Expected: Output showing 3 flight options with prices. If it errors, run `pip install flights` and retry. If zero results are returned with no error, this is a Google Flights rate-limit or regional block — the skill is installed correctly, proceed with remaining smoke tests.

- [ ] **Step 3: Verify slash command structure**

In Claude Code, type `/plan-trip` — verify it loads without error and asks for trip details.

- [ ] **Step 4: Verify directory structure is complete**

```bash
find . -name "AGENT.md" | sort
# Expected:
# ./agents/accommodation/AGENT.md
# ./agents/booking/AGENT.md
# ./agents/scout/AGENT.md
# ./agents/trip-planner/AGENT.md

find . -name "*.md" -path "*/workflows/*" | sort
# Expected: 8 workflow files across the 4 agents
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: foundation complete — agents, tools, flightclaw, slash commands"
```

---

## What's Next

**Plan 2 — hotelclaw skill:** Builds the Google Hotels + Airbnb + Booking.com scraper skill. Can be started immediately after this plan.

**Plan 3 — Dashboard:** Builds the FastAPI server with SSE, file watchers, and full frontend. Can be started in parallel with Plan 2.

Both plans are independent of each other and only depend on the foundation built here.
