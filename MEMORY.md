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
- **Full travel preferences** (flights, accommodation, food, travel style, loyalty accounts): `reference/yier-preferences.md`
  - Sensitive account numbers stored in `.env` (KRISFLYER_ID, ASIAMILES_ID, MARRIOTT_ID, HYATT_ID, TRIPCOM_ID, BOOKINGCOM_ID)

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
| Chope dining bookings: Method C (fully automated) | Tested end-to-end 2026-03-24; Playwright completes booking autonomously when user requests it | 2026-03-24 |
| Budget tracking: semi-automated | Confirmed bookings auto-written by Booking Agent; manual incidentals via dashboard | 2026-03-17 |
| Itinerary: living Markdown document, not one-shot | Both agent and user edit; persists across sessions; dashboard renders + edits | 2026-03-17 |
| Phase 2 parallelism: Claude Code Agent tool calls | Three workstreams (Scout + Accommodation + Activities) dispatched in single message as true parallel subagents | 2026-03-17 |
| Cron start: Phase 4 (after reconciliation) | Don't monitor options that haven't been chosen yet | 2026-03-17 |

---

## Chope Booking Capability

Fully automated via `scripts/chope_book.py`. Tested and confirmed working 2026-03-24 (Plu Bangkok, conf ID XPIA7JFOGEOX).

**To book a Chope restaurant:**
- Need: `slug` (URL path, e.g. `plu-bangkok`) + `rid` (widget ID, e.g. `plu1909bkk`)
- Find slug: `https://www.chope.co/bangkok-restaurants/list_of_restaurants`
- Find rid: inspect the booking widget URL after clicking Book Now on the restaurant page
- Credentials: `CHOPE_USERNAME` / `CHOPE_PASSWORD` in `.env`
- Script: `scripts/chope_book.py` — returns confirmation ID, adds calendar event
- Full flow documented in: `agents/booking/workflows/book-and-confirm.md` → Method C

**Known restaurants:**
| Restaurant | Slug | RID | Notes |
|---|---|---|---|
| Plu | `plu-bangkok` | `plu1909bkk` | Thai, Sathorn; lunch ends 1:45pm (not 2pm) |

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

## System Cron Jobs (persistent — do not recreate)

Registered in system crontab (`crontab -l` to verify). Survive session close and reboots.

| Job | Schedule | SDK Script | Log |
|---|---|---|---|
| Flight price check | Every 6h at :17 | `tools/monitor_flights.py` | `/tmp/travel-flights.log` |
| Hotel price check | Every 12h at :23 | `tools/monitor_hotels.py` | `/tmp/travel-hotels.log` |
| Daily briefing email | 08:00 HKT daily | `tools/daily_report.py` | `/tmp/travel-briefing.log` |

**Cron job standard — all jobs must follow this pattern:**
- Entry point: a Python script in `tools/` using `claude_agent_sdk`
- Runtime: `~/.pyenv/shims/python` (Python 3.12, has SDK installed)
- The script's prompt tells the agent which workflow markdown file to follow
- Crontab `PATH` line must include `/Users/yiercao/.local/bin` (for `claude`) and `/Users/yiercao/.pyenv/shims`
- Log to `/tmp/travel-[name].log`
- Never call skill scripts or workflow scripts directly from cron — always go through the SDK layer

**Do NOT use Claude Code CronCreate for these** — CronCreate jobs are session-only and die when Claude exits. The system crontab is the source of truth.

**To add a new cron job:**
1. Create `tools/[job_name].py` using the Agent SDK pattern (see existing scripts for template)
2. Add the entry to the system crontab: `crontab -e`
3. Update this table
4. Log to `output/changelog.md`

---

## Telegram Channel (always-on interface)

The session is accessible via Telegram bot `@yiersclaudebot`. Only Yier's Telegram account is on the allowlist.

**To start the persistent session after a reboot:**
```bash
screen -S concierge
cd "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge"
claude --channels plugin:telegram@claude-plugins-official
```
Then detach with **Ctrl+A, D**. Reattach with `screen -r concierge`.

- Bot token + pairing: saved in `.claude/channels/telegram/.env` (auto-loaded)
- Session dies on Mac shutdown — must be manually restarted after reboot
- No re-pairing needed after reboot — token and allowlist persist

**Requires:** Claude Code v2.1.80+, Bun installed at `~/.bun/bin/bun`

---

## Session Permissions (.claude/settings.json)

Project-level permissions are set in `.claude/settings.json`. The following are pre-approved (no prompt):
- `Bash(~/.pyenv/shims/python*)` / `Bash(python*)` — run Python tools and monitoring scripts
- `WebSearch` / `WebFetch` — web searches and page fetches
- `Write/Edit(trips/**)` — update trip state files
- `Write/Edit(output/**)` — write reports and changelog
- `Write/Edit(tools/**)` — create/update Python tool scripts
- `Write/Edit(scripts/**)` — create/update scripts (e.g. reservation scripts)
- `Write(.tmp/**)` — temporary working files
- All Gmail MCP tools (read, search, draft)
- Google Calendar MCP tools (read, create, update, delete events) — both `claude_ai_Google_Calendar` and `composio-google-calendar` servers

To add new permissions: edit `.claude/settings.json` → `permissions.allow` array.

---

## Recurring Issues & Solutions

*(none yet)*

---

## Workflow Registry

| File | Description |
|---|---|
| `workflows/plan-trip.md` | Phase 1→2→3 orchestration SOP — skeleton, parallel dispatch, reconciliation |
| `workflows/update-itinerary.md` | Edit living itinerary document in response to user requests |
| `workflows/budget-tracking.md` | Daily 08:00 cron report + on-demand budget check |
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
| Plan 2: hotelclaw skill | Complete | `skills/hotelclaw/` |
| Plan 3: Dashboard | Not started (after Plan 1) | TBD |
| Plan 4: arrival-cards skill | Scaffolded — build when ready | `skills/arrival-cards/SKILL.md` |

**arrival-cards roadmap (4 phases):**
1. Scaffold only (current) — agent reads SKILL.md, manually assembles pre-fill checklist
2. `scripts/check-required.py` — scan skeleton.json, surface deadlines, write STATUS.md action
3. `scripts/prefill.py` — auto-generate per-country checklist from trip files
4. Playwright automation for portals that allow it (Singapore ICA first candidate)

**Spec:** `docs/superpowers/specs/2026-03-17-travel-concierge-design.md`
