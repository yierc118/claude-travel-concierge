# Travel Concierge — Multi-Agent System Design

**Date:** 2026-03-17
**Status:** Approved
**Framework:** BITT (Brain, Identity, Tools, Tasks)

---

## Overview

A multi-agent travel concierge system built inside Claude Code. Serves dual purpose: a working personal travel planning tool and a showcase of Claude Code's agentic capabilities — parallel agents, cron schedules, and loops.

**Architecture:** BITT + live web dashboard (Option B)
**Primary stack:** Python tools, Node.js dashboard server, Claude Code native crons, MCP integrations (Gmail, Google Calendar)

---

## Agents

### Trip Planner Agent (Parent Coordinator)
- Main entry point for all user interaction
- Routes tasks to subagents during Phase 2
- Builds and refines itineraries interactively across sessions
- Owns budget ledger
- Runs daily 08:00 HKT cron: summarise alerts, update STATUS.md, send email report, surface inline if session active

### Scout Agent
- Monitors flight prices via FlightClaw (Google Flights, no API key)
- Tracks booked flight departure status via AirLabs API
- Cron: price check every 6h
- Cron: departure monitor every 2h on day-of travel
- Loop: active interactive monitoring when user is watching a specific route

### Accommodation Agent
- Researches and tracks hotels, Airbnb, and Google Hotels via hotelclaw skill (new)
- Cron: price check every 12h
- Maintains shortlist per trip in `accommodation.json`

### Booking Agent
- Assisted booking: fills forms, navigates to final confirmation page
- Pauses for user approval before any payment step
- Drafts confirmation emails via Gmail MCP

---

## Trip Lifecycle — Phase Model

### Phase 1 — Skeleton (Sequential, Interactive)
User chats with Trip Planner to define high-level structure: destinations, dates, transit legs between cities. Each decision informs the next. Output: `skeleton.json`.

### Phase 2 — Parallel Execution (Showcase moment)
Once skeleton is locked, three workstreams run concurrently using Claude Code's native parallel subagent dispatch (`superpowers:dispatching-parallel-agents`). All read from `skeleton.json`, write to separate state files, share no dependencies:

- **Scout Agent** — searches flights for each leg (e.g. SIN→KIX, domestic transfers, NRT→SIN) → writes `flights.json`
- **Accommodation Agent** — finds options per city+date range → writes `accommodation.json`
- **Trip Planner** — fills in daily activities within the locked structure → writes activity sections to `itinerary.md`

Each subagent is dispatched as a separate Claude Code Agent tool call in a single message (true parallelism). The parent Trip Planner waits for all three to complete before advancing to Phase 2.5.

### Phase 2.5 — Human Checkpoint
Dashboard surfaces parallel results: flight options, hotel shortlist, activity drafts. User reviews and approves before reconciliation runs. Prevents baking in choices the user would reject. Trip Planner writes `STATUS.md` with `phase: "2.5-checkpoint"` and waits — Phase 3 does not run until the user signals approval via the dashboard "Approve & Reconcile" button or the `/plan-trip` slash command.

### Phase 3 — Reconciliation (Sequential)
Trip Planner reads all Phase 2 outputs and synthesises: adjusts activities for flight arrival times, clusters activities by hotel location, resolves conflicts. Outputs a working draft `itinerary.md` — not a final product. Future sessions pick up from this file.

### Phase 4 — Ongoing (Active trip)
- Crons continue monitoring prices
- User and agent both edit `itinerary.md` as plans evolve
- Budget ledger updated as bookings confirmed
- AirLabs departure monitor activates ≤24h before booked flights

---

## Itinerary as Living Document

`itinerary.md` is a shared artifact — neither user nor agent owns it exclusively.

- Written in Markdown, human-readable and editable
- Agent reads current file state at the start of every session — continuity is automatic
- Dashboard renders it with an Edit button; saving writes directly to the file
- Agent and user edits both timestamped in the file footer
- Supports multiple trips — each has its own `itinerary.md` under `trips/[trip-id]/`

---

## Data Sources & Integrations

| Need | Tool | Notes |
|---|---|---|
| Flight price search + tracking | FlightClaw skill | Google Flights via `fli` library, no API key, cron-ready |
| Booked flight departure monitoring | AirLabs API | Day-of status, gate changes, delays |
| Hotel/Airbnb/Google Hotels | hotelclaw skill (new) | Combines Google Hotels scraping + Airbnb + Booking.com |
| Calendar integration | Google Calendar MCP | Block travel dates, add booking details |
| Email reports + booking drafts | Gmail MCP | Daily price report, booking confirmations |
| Budget tracking | budget_ledger.py | Reads confirmed bookings, manual incidentals |
| Dashboard | dashboard_server.py | FastAPI or Express, SSE for live updates |

---

## Price Classification

Used in both dashboard and email reports:

| Badge | Condition |
|---|---|
| 🟢 Buy now | ≥15% below historical average |
| 🟡 Good deal | 5–15% below average |
| 🟠 Fair | ±5% of average |
| 🔴 Above avg | >5% above average |
| ⏳ No data yet | Fewer than 3 data points collected |

**Historical average definition:**
- Computed per route per cabin class (e.g. SIN→NRT Economy is separate from SIN→NRT Business)
- Lookback window: all recorded price snapshots since tracking began, max 90 days
- Minimum 3 snapshots required before a badge is shown — before that, display "No data yet"
- Stored as a rolling array of `{ timestamp, price, currency }` objects in `flights.json` / `accommodation.json`
- Currency stored per snapshot; comparisons only made within the same currency (no cross-currency normalisation in v1)

---

## Daily 08:00 HKT Report (Cron)

Trip Planner runs daily and:
1. Reads all active trips from `/trips/*/`
2. Checks latest price snapshots vs historical averages for all flights and hotels
3. Classifies each item with badge
4. Writes summary to each trip's `STATUS.md`
5. Pushes update to dashboard (file watcher triggers SSE)
6. Sends structured email report via Gmail MCP — all trips in one email, grouped by trip
7. Surfaces inline alert if an active Claude session is running

Email subject format: `✈️ Travel Price Report — 17 Mar 2026`
Email structure: grouped by trip → flights section → accommodation section → classification badges

---

## File Structure

```
/
├── CLAUDE.md
├── MEMORY.md
├── .env                               # AirLabs key, etc. (never committed)
├── .env.example                       # Documented key names — safe to commit
│
├── /agents
│   ├── /trip-planner
│   │   ├── AGENT.md
│   │   └── /workflows
│   │       ├── plan-trip.md           # Phase 1→2→3 orchestration SOP
│   │       ├── update-itinerary.md    # Ongoing edit + feedback loop
│   │       └── budget-tracking.md
│   ├── /scout
│   │   ├── AGENT.md
│   │   └── /workflows
│   │       ├── search-flights.md
│   │       ├── monitor-prices.md      # Cron: every 6h
│   │       └── track-departure.md    # AirLabs: day-of monitoring
│   ├── /accommodation
│   │   ├── AGENT.md
│   │   └── /workflows
│   │       ├── find-accommodation.md
│   │       └── monitor-prices.md     # Cron: every 12h
│   └── /booking
│       ├── AGENT.md
│       └── /workflows
│           └── book-and-confirm.md
│
├── /skills
│   ├── /flightclaw                    # Existing skill
│   └── /hotelclaw                    # New skill — to be built
│
├── /tools
│   ├── airlabs.py                     # AirLabs API wrapper
│   ├── calendar_sync.py               # Google Calendar MCP helper
│   ├── budget_ledger.py               # Read/write budget JSON
│   └── dashboard_server.py           # Local server, SSE, file watchers
│
├── /trips
│   └── /[trip-id]                    # e.g. japan-2026-05
│       ├── skeleton.json              # Cities, dates, transit legs, current phase
│       ├── itinerary.md              # Living document
│       ├── flights.json              # Tracked + booked flights + price history
│       ├── accommodation.json        # Shortlisted + booked properties
│       ├── budget.json               # Confirmed costs + incidentals
│       └── STATUS.md                 # Current phase, pending actions, last alerts
│
├── /output
│   └── changelog.md
│
└── .claude/commands/
    ├── plan-trip.md
    ├── check-flights.md
    ├── find-hotels.md
    ├── check-budget.md
    └── dashboard.md
```

---

## Dashboard

**Tech:** Lightweight local server (FastAPI or Express) + Server-Sent Events for live updates. Watches `/trips` directory — no polling.

### Tabs

**Trips** — home screen, one card per trip showing phase, route summary, budget progress. Phase badge: grey (1) → blue animated (2) → amber (3) → green (4 active). `+ New Trip` button triggers Phase 1 in Claude.

**Scout** — all tracked flight legs grouped by trip. Matches screenshot reference: route, date, cabin, current price, min/avg/max range bar, % vs average, classification badge, tracking start date. `Track new route` button.

**Hotels** — same structure as Scout tab but for accommodation. Property name, dates, price/night, range bar, badge. `Add property` button.

**Itinerary** — trip selector at top (tab per active trip). Renders `itinerary.md` as formatted HTML. Edit button opens Markdown textarea; save writes to file. Shows agent last-updated and user last-edited timestamps.

**Budget** — per trip: confirmed bookings (locked), estimated categories, committed vs estimated total vs remaining.

**Crons** — showcase tab: all scheduled jobs with last run time, next run time, last result, status. Run now / Pause controls. View log. AirLabs monitor shows as inactive until a booked flight is ≤24h away.

---

## Slash Commands

| Command | Action |
|---|---|
| `/plan-trip` | Start Phase 1 — skeleton chat |
| `/check-flights` | Scout: search + optionally track a route |
| `/find-hotels` | Accommodation: search + add to shortlist |
| `/check-budget` | Trip Planner: show current budget state |
| `/dashboard` | Launch dashboard server, open in browser |

---

## Skills To Build

### hotelclaw (new)
Mirrors FlightClaw's structure and interface. Combines three sources — each is an independent fetcher that degrades gracefully if blocked.

**Sources:**
- **Google Hotels** — scraped via `google-search-results` or `serpapi` (free tier available); most reliable
- **Booking.com** — scraped via Playwright headless browser; requires no account for search results
- **Airbnb** — scraped via Playwright headless browser; public search pages accessible without login

**Anti-scrape handling:**
- Each source has an independent retry with exponential backoff (3 attempts, 2s / 4s / 8s)
- If a source fails after retries, it is skipped and flagged in output — the skill does not fail wholesale
- Playwright runs with randomised user-agent and 2–5s human-like delay between requests

**Tools:** `search_hotels`, `search_dates`, `track_property`, `check_prices`, `list_tracked`, `remove_tracked`
**Storage:** `skills/hotelclaw/data/tracked.json` with price history array per property
**Cron-ready:** `check-prices.py --threshold 5`
**MCP server:** same pattern as FlightClaw (`server.py`)
**Dependencies:** `playwright`, `serpapi` (or `google-search-results`), `mcp[cli]`

---

## Conventions & Definitions

### Trip ID
- Format: `[destination-slug]-[YYYY-MM]` — e.g. `japan-2026-05`, `europe-2026-06`
- Generated by Trip Planner at end of Phase 1, confirmed by user before directory is created
- If a conflict exists, append `-2` (e.g. `japan-2026-05-2`)
- Directory creation is the only file system action that requires explicit user confirmation

### "Active" Trip (for cron scope)
- A trip is **active** if `skeleton.json` contains `"status": "active"`
- Statuses: `active` (being planned/monitored), `completed` (travel date passed), `archived` (manually deactivated)
- Only `active` trips are included in cron runs and email reports
- Status transitions: Trip Planner sets `completed` automatically when the last travel date passes; user can set `archived` via dashboard

### "Booked" Flight (for AirLabs activation)
- A flight entry in `flights.json` is marked booked when `"booked": true` and `"flight_number"` is populated
- Booking Agent writes these fields after confirming a booking
- The Scout Agent's departure monitor cron checks `flights.json` on each run — if any entry has `"booked": true` and departure is within 24h, it activates the AirLabs check for that flight only

### Budget Write Model
- **Automatic writes:** Booking Agent writes confirmed booking cost to `budget.json` after user approves the booking
- **Manual incidentals:** User adds via dashboard Budget tab "Add expense" form — writes directly to `budget.json`
- **Estimates:** Trip Planner writes category estimates (food, activities, transport) during Phase 3; these are tagged `"type": "estimate"` and do not count as committed spend

### Dashboard Tech
- **Python FastAPI** — chosen for consistency with the Python tool layer; simpler to share data structures
- File watcher: `watchfiles` library (Python) — triggers SSE push on any change in `/trips/`
- SSE endpoint: `GET /events` — dashboard subscribes on load, receives updates without polling
- Dashboard frontend: vanilla HTML/CSS/JS served as static files from FastAPI — no build step required

### Scout Loop vs Cron
- **Cron (every 6h):** background price checks on all tracked routes across all active trips
- **Loop:** triggered when user runs `/check-flights` and chooses "Watch this route now" — runs `search_flights` repeatedly at a user-specified interval (e.g. every 30 min) within the current Claude session only; terminates when session ends or user cancels

### "Surfaces inline" Clarification
- This means: if the user is in an active Claude Code session when the 08:00 cron fires, the cron output is written to `STATUS.md` and the dashboard updates; there is **no** mechanism to inject text into the active session
- The user sees it on their next message or via the dashboard — no special session detection required

---

## Constraints & Guardrails

- Booking Agent never completes a payment without explicit user approval
- Agents never create new workflow files without user confirmation
- Paid API calls (AirLabs) flagged before running
- All agent changes logged to `/output/changelog.md`
- `.env` never committed — documented in `.env.example`
- Dashboard server runs locally only (127.0.0.1)
- Scraper failures are non-fatal — logged to `output/changelog.md`, flagged in dashboard and email report with ⚠️ indicator, cron continues with available data
- Stale data policy: if a price snapshot is >18h old (3 missed 6h cron cycles), dashboard shows a ⚠️ stale indicator next to that route's price
- `.env.example` documents all required keys: `AIRLABS_API_KEY`, `SERPAPI_KEY` (optional, for hotelclaw Google Hotels)
