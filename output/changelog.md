# Changelog

Agent-maintained. Each automated run appends a brief entry.

---

## 2026-03-26T12:33+08:00 — Accommodation cron: checked 12 properties across 1 trip. Alerts: 0
⚠️ HotelClaw unavailable — `serpapi` module not installed (`pip install serpapi` required). No live prices fetched. last_checked timestamps updated. Prices remain at knowledge-based estimates from 2026-03-26.

---

## 2026-03-26T12:21+08:00 — Scout cron: checked 4 routes across 1 trip. Alerts: 0
⚠️ FlightClaw unavailable — `fast_flights` module not installed (`pip install fast_flights` required). No live prices fetched. last_checked timestamps updated. Prices remain at knowledge-based estimates from 2026-03-26.

---

## 2026-03-24 — Chope booking automation (Method C)

**What changed:**
- Added `scripts/chope_book.py` — reusable Playwright script for end-to-end Chope restaurant booking
- Updated `agents/booking/workflows/book-and-confirm.md` — added Method C section with full technical reference
- Updated `MEMORY.md` — added Chope Capability section with known restaurants table and quick-reference

**What was learned (from live test — Plu Bangkok, conf XPIA7JFOGEOX):**
- Chope booking widget opens as a new browser tab (`target="_blank"`) — must use `context.on("page")` listener to capture it
- Widget path is `booking.chope.co/widget/#/booking_index` — date/time NOT passed in URL, must be selected inside widget
- Calendar uses Vue components with `.vc-day.id-YYYY-MM-DD` selectors
- Time slots are `.time_item` divs — use exact string match (substring match fails: `"2:00 pm" in "12:00 pm"` is True)
- "Book table" button disabled until T&C checkbox (`.nav-confirmation-row input[type='checkbox']`) is clicked
- The form has a separate "Save" button for inline name editing — do not click that
- Plu last lunch slot: 1:45pm (not 2pm)

---

## 2026-03-20 (session 4)

### 🗂 crons.json — restructured into active/conditional registry

Replaced the single `planned` array with two sections:
- `active` — the 3 persistent system cron jobs (monitor-flights, monitor-hotels, daily-briefing) now visible in dashboard
- `conditional` — departure check (manual register/deregister per trip); fixed script reference from `tools/airlabs.py` (raw tool) to `tools/monitor_departure.py` (SDK wrapper, not yet built — noted as scaffold)

Dashboard `GET /crons` now reflects the full cron picture.

### 📋 skills/arrival-cards — scaffolded

Created `skills/arrival-cards/SKILL.md` with country reference for SG, JP, TH, UK, AU. Field mappings point to trip state files. 4-phase implementation roadmap included. Added Plan 4 to MEMORY.md implementation status.

---

## 2026-03-18 (session 3)

### 🔧 hotelclaw — fixed SERPAPI_KEY not loading in subprocesses

**Problem:** `scrapers.py` used `os.environ.get("SERPAPI_KEY")` but the key was only set in `.env`. When scripts were invoked directly (or via cron without `export`), Python subprocesses couldn't inherit unexported shell variables — so Google Hotels silently skipped on every run.

**Fix:** Added `python-dotenv` load at the top of `scrapers.py`:
```python
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(...), ".env"))
```
Now loads `.env` automatically regardless of how the script is invoked.

**Note for crontab:** The existing `source .env` in cron entries is now redundant (but harmless). The script is self-sufficient.

### ✈️ japan-2026-05 — Phase 3 complete, hotels + flights tracking live

- **Departure corrected:** SIN (Singapore), not HKG — skeleton.json and flights.json updated
- **FlightClaw fixed** (see 2026-03-18 entry below) — live SIN↔NRT prices now working
- **Flights tracked:** NRT→SIN May 25 added to `skills/flightclaw/data/tracked.json`; system cron `17 */6 * * *` added for flight price checks → `/tmp/flightclaw.log`
- **Hotels tracking:** 8 Japan properties in `skills/hotelclaw/data/tracked.json` with live opening prices:
  - Tokyo: Gracery Shinjuku $198, Granbell $123
  - Hakone: Itoen Yumoto $193, Okuyumoto $224, Tenseien $155
  - Karuizawa: Twin-Line $133, Rosso $173, BEB5 ~$175 est. (not on Google Hotels)
- **Hotel Indigo Karuizawa removed** from shortlist — live price $302 exceeds $250/night cap
- **Itinerary saved:** `trips/japan-2026-05/itinerary.md` — 10-day draft, Phase 4-active

---

## 2026-03-18

### 🔧 FlightClaw — rewritten from `fli` to `fast_flights`

**Problem:** All FlightClaw scripts (`search-flights.py`, `track-flight.py`, `check-prices.py`, `search_utils.py`, `helpers.py`) imported a `fli` package that does not exist on PyPI and was never installable. Scripts failed with `ModuleNotFoundError: No module named 'fli'` on every run.

**Fix:** Rewrote all scripts to use `fast_flights` (installed via `pip install fast-flights`).

**How `fast_flights` works:**
- Scrapes Google Flights directly at `https://www.google.com/travel/flights`
- Uses `primp` (Rust HTTP client, impersonates Chrome 126) to bypass bot detection
- Fallback: Playwright if `primp` request fails
- HTML parsed with `selectolax`
- No paid API key required
- Returns `Result(current_price, flights=[Flight(...)])` — price as formatted string (e.g. `"SGD 390"`), not a float

**API changes (old `fli` → new `fast_flights`):**
- `FlightSearchFilters` / `FlightSegment` / `PassengerInfo` → `FlightData(date, from_airport, to_airport)` + `Passengers(adults=N)` + `get_flights(...)`
- `SeatType.ECONOMY` → `"economy"` (plain string)
- `MaxStops.NON_STOP` → `0` (int); `None` = any stops
- `TripType.ONE_WAY` → `"one-way"` (plain string)
- `flight.legs[0].airline.name` → `flight.name` (airline string, no leg detail)
- `flight.price` (float) → `flight.price` (formatted string — use `parse_price_str()` to extract float)
- No per-leg detail (flight number, departure/arrival airport names) — only summary level

**Known limitation:** `fast_flights` returns Google's "best deals" sort, which surfaces budget carriers (Scoot, XiamenAir) first. Full-service carriers (SQ, CX, JAL) may not appear in top results. For SQ/CX pricing, check directly on their sites or Google Flights manually.

**Files updated:** `skills/flightclaw/scripts/search-flights.py`, `track-flight.py`, `check-prices.py`, `search_utils.py`, `helpers.py` — and synced to `reference/flightclaw/scripts/`.

---

## 2026-03-17 (session 2)

### ⚙️ System crontab — ALREADY CONFIGURED (do not re-add)
Two cron jobs are registered in the system crontab (`crontab -e`) and persist across sessions and reboots:
- **Hotel price check** — `23 */12 * * *` → `skills/hotelclaw/scripts/check-prices.py` → logs to `/tmp/hotelclaw.log`
- **Daily briefing email** — `0 8 * * *` (08:00 HKT) → `workflows/daily-briefing.py` → sends HTML email to caoyier118@gmail.com → logs to `/tmp/travel-briefing.log`

**Do NOT use Claude Code CronCreate for these** — those are session-only and die when Claude exits. The system crontab entries are the source of truth. To verify: run `crontab -l` and look for `# Travel Concierge` entries. To update schedules, edit with `crontab -e`.

### Changes
- **hotelclaw fully activated** — Google Hotels (SerpAPI) returns live prices ✅. Fixed: Python 3.9 `Optional[float]` compat; serpapi import updated to `serpapi.Client` (new SDK); Airbnb source removed (consistent timeouts). Booking.com returns names+URLs only (prices JS-rendered, not parseable).
- **agents/accommodation/AGENT.md updated** — hotelclaw is now the primary tool; Google Hotels is price source; Booking.com is discovery/link source; web search is fallback.

## 2026-03-17
- Project scaffolded. Foundation plan implemented.
- hotelclaw skill built: `skills/hotelclaw/` — Google Hotels (SerpAPI), Booking.com (Playwright), Airbnb (Playwright) scrapers with full tracking, MCP server, and CLI scripts mirroring flightclaw interface.
- Dashboard built (Plan 3): `tools/dashboard_server.py` (FastAPI + SSE + file watcher), `tools/static/` (index.html, style.css, app.js) — live trip dashboard with Trips, Scout, Hotels, Itinerary, Budget, and Crons tabs.

### Review session — Tasks 1-9, Plan 2, Plan 3

**Security fixes applied:**
- `skills/flightclaw/data/tracked.json` cleared to `[]` and added to `.gitignore` — personal travel data no longer committed
- `tools/dashboard_server.py` — path traversal vulnerability fixed: added `_safe_trip_dir()` that validates all `trip_id` paths stay within `TRIPS_DIR`; error messages no longer leak internal file paths; `ItineraryUpdate.content` capped at 500k chars
- `tools/static/app.js` — DOM XSS fixed: added `esc()` helper applied to all data interpolations; `markdownToHtml()` now escapes HTML before processing; `onclick` string injections replaced with event delegation and `addEventListener`; SSE `EventSource` leak fixed
- `skills/hotelclaw/helpers.py` — `save_tracked()` now uses atomic write (temp file + `os.replace()`)
- `skills/hotelclaw/scrapers.py` — brittle Airbnb `._tyxjp1` CSS selector replaced with stable `aria-label`/`data-testid` selectors; added zero-price warning log

**Workflow updates:**
- `agents/booking/AGENT.md` + `book-and-confirm.md` — scope changed to hotels, dining, and events (not flights); PII scope clarified to name + phone number only; "For Flights" section removed; "For Accommodation" section expanded with specific steps; "For Dining / Events" section added; full error handling section added; price verification step added
- `agents/accommodation/workflows/find-accommodation.md` — error handling added (skip-and-continue per city)

**Architecture refactor — trip-planner promoted to root coordinator:**
- `agents/trip-planner/` deleted — coordinator role merged into `CLAUDE.md` (no more redundant identity)
- `workflows/` created at project root; 3 workflow files moved from `agents/trip-planner/workflows/`: `plan-trip.md`, `budget-tracking.md`, `update-itinerary.md`
- `CLAUDE.md` updated with "Your Role in This Project" section: coordinator identity, scope, voice, constraints, subagent registry, workflow pointers, key reference files; file structure updated
- `.claude/commands/plan-trip.md` and `check-budget.md` updated to reference `workflows/` directly (removed now-deleted AGENT.md load step)
- `MEMORY.md` workflow registry paths updated to `workflows/`

**Subagent model assignments:**
- `agents/trip-planner/AGENT.md` → deleted (merged into root)
- `agents/scout/AGENT.md` → `model: haiku`
- `agents/accommodation/AGENT.md` → `model: sonnet`
- `agents/booking/AGENT.md` → `model: sonnet`

**User travel preferences stored:**
- `reference/yier-preferences.md` created — full flight, accommodation, food, and travel style preferences; loyalty account numbers referenced by env var name
- `.env` and `.env.example` updated with 6 loyalty/FF account variables: `KRISFLYER_ID`, `ASIAMILES_ID`, `MARRIOTT_ID`, `HYATT_ID`, `TRIPCOM_ID`, `BOOKINGCOM_ID`
- `agents/scout/AGENT.md` and `agents/accommodation/AGENT.md` updated to load preferences file first
- `MEMORY.md` updated with pointer to preferences file

**Booking Agent — Method B (Vapi phone calls) added:**
- `tools/vapi_call.py` created — outbound Vapi call tool; inline assistant config (no pre-built Vapi assistant needed); language-aware voices (EN/JA via 11Labs); polls until call ends; saves full transcript + result JSON to `trips/[trip-id]/confirmations/`
- `agents/booking/AGENT.md` updated — added explicit platform list per category (hotels: Booking.com/Trip.com/direct; restaurants: TableCheck/OpenTable/Resy; activities: Airbnb Experiences/Klook/direct); added Method A/B distinction; added screenshot instruction; added `reference/yier-preferences.md` as first-load reference; added `tools/vapi_call.py` to tools list
- `agents/booking/workflows/book-and-confirm.md` updated — Method A: added screenshot steps (pre-fill + confirmed), prefer direct site logic; Method B: full Vapi phone workflow (script generation in target language, call command, transcript review, `📞 CALL RESULT` report format, state file updates after confirmation); Vapi-specific error handling added (unanswered, ambiguous result)
- `.env` and `.env.example` updated with `VAPI_API_KEY` and `VAPI_PHONE_NUMBER_ID`
- Smoke test passed: env vars load correctly, `requests` available

**Open items for next implement pass (see REVIEW.md for full list):**
- Create `requirements.txt` with pinned dependencies
- Fix `airlabs.py`: unused `date` param, `response.json()` error path, silent null response
- Fix `budget_ledger.py`: error handling on read, atomic write, UTC/HKT timestamp convention
- Fix `test_calendar_sync.py`: remove unused imports
- Fix deprecated `@app.on_event("startup")` in `dashboard_server.py`
- hotelclaw: add retry with exponential backoff, fix Booking.com date format, URL-encode city param, add date validation, implement `search_dates` tool, add tests
- Run `pytest tests/ -v` and create final commit: `feat: foundation complete`

[2026-03-20] Cron layer migrated to Claude Agent SDK
- Installed claude-agent-sdk 0.1.49 (Python 3.12 via pyenv)
- Created tools/monitor_flights.py — Agent SDK wrapper for scout/workflows/monitor-prices.md
- Created tools/monitor_hotels.py — Agent SDK wrapper for accommodation/workflows/monitor-prices.md
- Created tools/daily_report.py — Agent SDK wrapper for workflows/budget-tracking.md (daily report)
- Updated system crontab: all 3 travel cron jobs now use SDK scripts via ~/.pyenv/shims/python
- Fixed: daily briefing cron was pointing at workflows/daily-briefing.py (did not exist) — now fixed
- Added PATH line to crontab so `claude` CLI is discoverable by cron
- Updated MEMORY.md: cron job table + standard documented for all future jobs
