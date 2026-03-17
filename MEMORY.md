# Memory

Agent-maintained. Updated each session. Do not edit manually unless correcting an error.

---

## Project Identity

> **Role:** You are a multi-agent travel concierge. You help plan, monitor, and execute trips through a team of specialised subagents.
>
> **Context:** This is both a personal travel planning tool and a showcase of Claude Code's agentic capabilities — parallel agents, cron schedules, and loops. Built on the BITT framework. The user is a non-technical builder (vibe coder) who understands architecture and product but is not writing code from scratch.
>
> **Voice & Style:** Direct, actionable, low-fluff. Surface decisions clearly. Never auto-book or auto-pay — always pause for approval. Ask clarifying questions before starting Phase 1.
>
> **Output:** Trip state files in `/trips/[trip-id]/`, itinerary as `itinerary.md`, daily email reports via Gmail MCP.

---

## Learned Preferences

- Prefers to describe WHAT he wants built, not HOW — take ownership of implementation decisions
- When implementation choices have trade-offs, surface them clearly and make a recommendation
- Does not want to be asked about confirmation on implementation details unless there's genuine ambiguity
- Wants cost estimates / credit usage flagged before any paid API call (e.g. AirLabs)
- Timezone: Asia/Hong_Kong (UTC+08:00) for all date/time operations

---

## Past Decisions

| Decision | Rationale | Date |
|---|---|---|
| Architecture: BITT + live web dashboard (Option B) | Real-time dashboard best for showcase; keeps everything Claude Code-native | 2026-03-17 |
| Flight price monitoring: FlightClaw skill | Free (Google Flights via `fli` library), cron-ready, no API key, consistent with existing reference skill | 2026-03-17 |
| Booked flight tracking: AirLabs API | Reliable real-time departure data; only activated day-of for booked flights to minimise credit usage | 2026-03-17 |
| Accommodation: hotelclaw (new skill, Plan 2) | Combines Google Hotels + Airbnb + Booking.com scraping; graceful degradation per source | 2026-03-17 |
| Dashboard tech: Python FastAPI + SSE + vanilla JS | Consistent with Python tool layer; no build step; watchfiles for live updates | 2026-03-17 |
| Booking Agent: Level B (assisted, pause before payment) | User retains full payment control; no stored credentials | 2026-03-17 |
| Budget tracking: semi-automated | Confirmed bookings auto-written by Booking Agent; manual incidentals via dashboard | 2026-03-17 |
| Itinerary: living Markdown document, not one-shot | Both agent and user edit; persists across sessions; dashboard renders + edits | 2026-03-17 |
| Phase 2 parallelism: Claude Code Agent tool calls | Three workstreams (Scout + Accommodation + Activities) dispatched in single message as true parallel subagents | 2026-03-17 |
| Cron start: Phase 4 (after reconciliation) | Don't monitor options that haven't been chosen yet | 2026-03-17 |

---

## Known Constraints

- Booking Agent must NEVER complete a payment — always stop at confirmation page and wait for user
- AirLabs API costs credits — only call when `booked == true` AND departure is within 24h
- Agents must never create new workflow files without user confirmation
- All agent changes logged to `/output/changelog.md`
- `.env` never committed — keys documented in `.env.example`
- Dashboard runs locally only (127.0.0.1)
- Scraper failures are non-fatal — log and continue, flag with ⚠️ in dashboard and email

---

## Recurring Issues & Solutions

*(none yet)*

---

## Workflow Registry

| File | Description |
|---|---|
| `agents/trip-planner/workflows/plan-trip.md` | Phase 1→2→3 orchestration SOP — skeleton, parallel dispatch, reconciliation |
| `agents/trip-planner/workflows/update-itinerary.md` | Edit living itinerary document in response to user requests |
| `agents/trip-planner/workflows/budget-tracking.md` | Daily 08:00 cron report + on-demand budget check |
| `agents/scout/workflows/search-flights.md` | Phase 2 flight search via FlightClaw, writes flights.json |
| `agents/scout/workflows/monitor-prices.md` | 6h cron — check all tracked routes, append price history, alert on drops |
| `agents/scout/workflows/track-departure.md` | Day-of AirLabs departure monitor for booked flights |
| `agents/accommodation/workflows/find-accommodation.md` | Phase 2 hotel/rental search, writes accommodation.json |
| `agents/accommodation/workflows/monitor-prices.md` | 12h cron — check tracked accommodation prices |
| `agents/booking/workflows/book-and-confirm.md` | Assisted booking flow — fill forms, pause at payment, update state files |

---

## Implementation Status

| Plan | Status | Path |
|---|---|---|
| Plan 1: Foundation | Ready to implement | `docs/superpowers/plans/2026-03-17-foundation.md` |
| Plan 2: hotelclaw skill | Not started (after Plan 1) | TBD |
| Plan 3: Dashboard | Not started (after Plan 1) | TBD |

**Spec:** `docs/superpowers/specs/2026-03-17-travel-concierge-design.md`
