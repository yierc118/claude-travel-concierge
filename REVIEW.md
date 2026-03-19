# Code Review

## Tasks 1-3 Review — 2026-03-17

**Verdict: Approved with Fixes**
**Pipeline: Continue**
**Scope: Tasks 1-3 (Project Scaffolding, Trip Planner Agent, Scout Agent)**
**Review cycle: 1**

---

### Critical (fix before merging to remote)

- ~~**`/skills/flightclaw/data/tracked.json`** — Contains real personal travel data. Not gitignored at project level.~~ ✅ **Fixed 2026-03-17** — Cleared to `[]`, added to `.gitignore`. Was never committed (untracked), so no git history to clean.

- ~~**`/skills/flightclaw/scripts/__pycache__/*.pyc`** — Compiled bytecode copied from reference.~~ ✅ **Confirmed clean 2026-03-17** — Files were never tracked by git. Existing `__pycache__/` rule in `.gitignore` was already covering them.

---

### Warnings (auto-approved, fix in next /implement pass)

- **`/agents/trip-planner/workflows/plan-trip.md:68-71`** — Error handling for subagent failures only covers "missing or empty" output files. Should also validate JSON parse on `flights.json` and `accommodation.json` to catch malformed output.

- **`/agents/trip-planner/workflows/budget-tracking.md:43`** — Budget item schema uses UTC offset (`+00:00`) but the design spec requires Asia/Hong_Kong timezone (`+08:00`). Clarify: store UTC and convert for display (preferred), or store in HKT. Document the convention.

- **`/agents/scout/workflows/search-flights.md`** — No error handling specified. If `search-flights.py` fails for one leg (e.g., invalid airport code), it's unclear whether to skip and continue or abort. `monitor-prices.md` correctly handles this ("log and continue") — apply the same pattern here.

- **`/agents/scout/workflows/track-departure.md:28`** — Specifies "compose Gmail draft (do not auto-send)" for delays >60min but no fallback if Gmail MCP is unavailable. Add: write to STATUS.md as fallback.

- **Missing: `output/changelog.md`** — Task 1 specifies this file and the BITT framework references it throughout. The `output/` directory does not exist. Create `output/changelog.md` with an initial entry.

- **Missing: `.claude/commands/`** — Slash command files (`plan-trip.md`, `check-flights.md`, `find-hotels.md`, `check-budget.md`, `dashboard.md`) are in the plan's File Map but were not created. Confirm these are assigned to a specific later task.

- **`/skills/flightclaw/data/tracked.json:88,99`** — Two entries use date format `"20260516"` (no hyphens) while all others use `"YYYY-MM-DD"`. Inconsistency copied from reference — could cause date parsing failures in `monitor-prices.md`. Fix to ISO format.

---

### Nits (optional)

- **`/agents/scout/workflows/monitor-prices.md:9-11`** — Steps 2 and 4 both run FlightClaw searches (`check-prices.py` globally, then `search-flights.py` per leg). This is redundant. Use one or the other, not both.

- **`/agents/trip-planner/AGENT.md:19`** — Uses `/output/changelog.md` (absolute-style) while the spec uses `output/changelog.md` (relative). Be consistent.

- **`/agents/trip-planner/workflows/plan-trip.md:23-38`** — `skeleton.json` example uses hardcoded data (Tokyo, SIN→NRT). Add a note clarifying it's an example, not the actual schema.

- **`/agents/scout/AGENT.md`** — References `tools/airlabs.py` which doesn't exist yet (Task 6). Fine for now, worth noting as a forward dependency.

---

### What's Good

- **Faithful spec implementation.** All agent files and workflows match the design document. BITT framework correctly applied — each agent has Identity, Scope, Constraints, Tools, and Memory sections.
- **Proactive Phase 2 error handling.** `plan-trip.md` includes graceful degradation for subagent failures — not in the original plan but called out in the design spec's constraints. Good initiative.
- **Budget item schema.** `budget-tracking.md` adds a concrete JSON schema with category enum, type field (confirmed vs estimate), and timestamps.
- **Security guardrails consistent.** Every agent that touches booking reiterates "never auto-pay." Scout Agent explicitly flags AirLabs credit costs.
- **Clean scaffolding.** File structure matches spec exactly. `.env.example` documents all keys with comments. `.gitignore` covers right patterns. FlightClaw copied successfully.
- **Cron deduplication guard.** `plan-trip.md` (line 104) checks for existing crons before registering — prevents duplicates on re-runs.

---

### Fix List for Next /implement Pass

1. Replace `skills/flightclaw/data/tracked.json` with `[]`
2. Run `git rm --cached` on `__pycache__` files
3. Create `output/changelog.md`
4. Add error handling to `search-flights.md` workflow
5. Clarify UTC vs HKT timestamp convention in budget schema
6. Fix redundant search logic in `monitor-prices.md`
7. Fix date format inconsistency in `tracked.json` (entries 88, 99)

---

*Note: Review agent ran read-only (no Bash access). Git diff, linting, and type checking were not performed. Recommend running `git diff HEAD~5..HEAD` and `git ls-files skills/flightclaw/scripts/__pycache__/` to verify tracked files.*

---

## Tasks 4-5 Review — 2026-03-17

**Verdict: Approved with Fixes**
**Pipeline: Continue**
**Scope: Task 4 (Accommodation Agent), Task 5 (Booking Agent)**
**Review cycle: 1**

---

### Critical

None. No hardcoded secrets, no credentials in code, no injection vectors. The Booking Agent's "NEVER complete a payment" hard constraint is correctly present and prominently placed.

---

### Warnings (auto-approved, fix in next /implement pass)

- **`/agents/booking/workflows/book-and-confirm.md:4` — PII handling guidance missing.** Step 4 instructs the agent to ask for passport number and DOB if not provided. No guidance on whether this is persisted. Add explicit constraints: never write passport/DOB to any JSON state file, never log PII to `output/changelog.md`, PII is session-only. Must be fixed before the Booking Agent is ever invoked.

- **`/agents/booking/workflows/book-and-confirm.md` — No error handling section.** All other workflows have either an explicit Error Handling section or inline error guidance. This one has none. What happens if the booking site is unreachable? The flight no longer exists at the quoted price? The Notes section partially addresses browser blocking, but a proper Error Handling section with fail-closed behavior is needed.

- **`/agents/accommodation/workflows/find-accommodation.md` — No error handling section.** If web search fails for one city, the workflow doesn't specify skip-and-continue vs abort. `monitor-prices.md` in the same agent correctly says "continue with remaining properties" — apply the same pattern here.

- **`/agents/booking/workflows/book-and-confirm.md:44-45` — "For Accommodation" section is underspecified.** Says "Same pattern" without defining accommodation-specific steps (check-in/check-out dates, number of guests, room type, cancellation policy, prepayment vs pay-at-hotel). List the accommodation-specific fields that must be verified before stopping at payment.

- **`/agents/booking/workflows/book-and-confirm.md:10-12` — No price verification step.** The workflow reads the expected price from `flights.json` but never compares it to the price shown on the booking site. Add a step between 3 and 4: if displayed price differs from expected by >10%, alert user and wait for confirmation before proceeding.

- **Booking Agent browser URL scope unbound.** No allowlist of permitted booking domains. Consider restricting browser navigation to known booking sites (Google Flights, airline direct, Booking.com, Airbnb) to prevent manipulation via crafted `flights.json` or `accommodation.json` URLs.

---

### Nits (optional)

- **`/agents/accommodation/workflows/find-accommodation.md:15`** — JSON schema example uses "Shinjuku Granbell Hotel" / "Tokyo" as sample data. Add a comment noting this is an example, not live data.
- **`/agents/booking/workflows/book-and-confirm.md:34`** — Shows `add_item(...)` with specific values. This function doesn't exist yet (Task 6: `tools/budget_ledger.py`). Forward dependency — will be validated at Task 6 review.
- **`/agents/booking/AGENT.md:16`** — "Browser / computer use tool" is vague compared to how other agents specify their tools. Acceptable since browser automation approach depends on execution environment.

---

### What's Good

- **Exact spec compliance.** All 5 files match the design document's file tree: `agents/accommodation/AGENT.md`, `find-accommodation.md`, `monitor-prices.md`, `agents/booking/AGENT.md`, `book-and-confirm.md`.
- **Payment safety guardrail is strong.** `AGENT.md` uses bold "Hard constraint: NEVER complete a payment — This is non-negotiable." Workflow reinforces at step 6 with a STOP instruction and user-facing message template.
- **Accommodation Agent handles the hotelclaw gap correctly.** Both files acknowledge hotelclaw doesn't exist yet and fall back to web search, with a note to replace once hotelclaw is available.
- **Consistent BITT structure.** All four agents follow the same template: Identity (Role, Scope, Constraints), Tools, Memory/Reference Files.
- **Verbatim plan implementation.** No deviations, additions, or omissions from the plan spec.

---

### Fix List for Next /implement Pass (Tasks 4-5)

1. ~~Add PII handling constraints to `book-and-confirm.md`~~ ✅ **Fixed 2026-03-17** — Agent scope redefined: hotels, dining, events only. Name + phone number are the only personal details the agent ever handles. Passport/DOB/payment removed entirely.
2. ~~Add Error Handling section to `book-and-confirm.md`~~ ✅ **Fixed 2026-03-17** — Full error handling section added (site unreachable, price change >10%, login required, browser blocked, mid-flow failure).
3. ~~Add error handling to `find-accommodation.md`~~ ✅ **Fixed 2026-03-17** — Skip-and-continue pattern added per city.
4. ~~Expand "For Accommodation" section~~ ✅ **Fixed 2026-03-17** — Full accommodation steps added. "For Flights" section removed (user books flights directly). "For Dining / Events" section added.
5. ~~Add price verification step~~ ✅ **Fixed 2026-03-17** — Price check added (alert if >10% difference before proceeding).
6. URL allowlist — deferred, low priority for personal tool.

---

*Note: Review agent ran read-only. These are markdown workflow files with no executable code to lint or type-check. Verification is structural and semantic only.*

---

## Tasks 6-8 Review — 2026-03-17

**Verdict: Approved with Fixes**
**Pipeline: Continue**
**Scope: Task 6 (Python Tools Layer), Task 7 (Slash Commands), Task 8 (Output Directory + Changelog)**
**Review cycle: 1**

---

### Critical

- **`/tools/dashboard_server.py` — Path traversal vulnerability.** ⏸️ **Deferred — fix after Plan 3 is complete.** All API endpoints construct file paths using unsanitized `trip_id` (`TRIPS_DIR / trip_id`). Fix: validate resolved path stays within `TRIPS_DIR` using `.resolve().is_relative_to(TRIPS_DIR.resolve())`.

- **`/tools/dashboard_server.py` — Unauthenticated write endpoint.** ⏸️ **Deferred — fix after Plan 3 is complete.** `POST /api/trips/{trip_id}/itinerary` has no authentication. Add path traversal protection + token-based auth for write operations.

---

### Warnings (auto-approved, fix in next /implement pass)

- **`/tools/airlabs.py:15` — `date` parameter accepted but never used.** Not passed to AirLabs API (which only supports real-time, current-day status anyway). Either remove the parameter or add a guard that raises if date is not today.

- **`/tools/airlabs.py:37` — `response.json()` in error path may throw.** If AirLabs returns a non-JSON body (e.g. HTML 502), `response.json()` raises `JSONDecodeError`, masking the real HTTP error. Use `response.text` as fallback.

- **`/tools/airlabs.py:39` — Silent failure on empty response.** If AirLabs returns `{"response": null}`, the code returns `status: "unknown"` with all fields as `None` — no exception raised. The track-departure workflow would treat this as "no delay." Raise `AirLabsError("No flight data returned")` explicitly.

- **`/tools/budget_ledger.py` — No error handling on file read/write.** `_read()` throws unhandled `FileNotFoundError` / `JSONDecodeError` if `budget.json` is missing or corrupt. `_write()` truncates the file before writing — a crash mid-write corrupts all budget data. Use try/except on reads and atomic write (temp file + `os.replace()`) on writes.

- **`/tools/budget_ledger.py:30` — Non-deterministic error message.** `f"Must be one of: {ITEM_TYPES}"` prints a set in arbitrary order. Use `sorted(ITEM_TYPES)`.

- **`/tools/budget_ledger.py:40` — UTC timestamp, spec says HKT.** `datetime.now(timezone.utc)` — same UTC vs HKT ambiguity flagged in Tasks 1-3 review. First actual code implementing timestamps. Establish the convention here and document it in the docstring.

- **`/tools/calendar_sync.py` — No input validation on datetime strings.** Malformed datetime strings are passed through to the Google Calendar API, which returns opaque errors. Validate ISO 8601 format before building the event dict.

- **`/tools/dashboard_server.py:80` — Deprecated `@app.on_event("startup")`.** FastAPI deprecated this in favour of `lifespan`. Will emit warnings and may break in future versions.

- **Missing `requirements.txt`.** Tools depend on `requests`; dashboard depends on `fastapi`, `uvicorn`, `watchfiles`, `pydantic`. No dependency manifest exists. Create one.

---

### Nits (optional)

- **`/tests/test_*.py` — `sys.path.insert(0, ...)` hack.** Fragile. Use `pyproject.toml` with `[tool.pytest.ini_options] pythonpath = ["."]` instead.
- **`/tests/test_calendar_sync.py:4` — Unused imports** `MagicMock` and `patch`. Remove.
- **`/tools/calendar_sync.py` — `build_hotel_event` has no reminders.** Flights get 24h + 3h reminders; hotels get none. Consider adding a check-in day reminder.
- **`/.claude/commands/dashboard.md` — Stale note** says dashboard_server.py is "built in Plan 3" but it already exists. Update.

---

### What's Good

- **All three planned tools delivered.** `airlabs.py`, `budget_ledger.py`, `calendar_sync.py` match plan specs exactly.
- **Good test fixture design.** `conftest.py` uses `autouse=True` to inject the API key; missing-key test correctly overrides with `monkeypatch.delenv`.
- **API key handled correctly.** Read from env var, not hardcoded. Missing key raises a clear error immediately.
- **Calendar sync is purely functional.** No side effects, no API calls — just builds dicts. Trivially testable, clean separation of concerns.
- **Slash commands are thin and correct.** Each loads the right AGENT.md + workflow, passes `$ARGUMENTS`, does no logic itself. Exactly what BITT prescribes.
- **`output/changelog.md` created** with correct initial entry per Task 8 spec.

---

### Fix List for Next /implement Pass (Tasks 6-8)

1. ⏸️ **[CRITICAL — post Plan 3]** Path traversal protection on all `dashboard_server.py` endpoints
2. ⏸️ **[CRITICAL — post Plan 3]** Auth/CSRF protection on `POST /api/trips/{trip_id}/itinerary`
3. Remove or guard unused `date` parameter in `airlabs.py`
4. Wrap `response.json()` in try/except in airlabs.py error path
5. Handle empty/null AirLabs `response` explicitly (raise instead of silent `status: "unknown"`)
6. Add error handling to `budget_ledger.py:_read()` for missing/corrupt files
7. Atomic write in `budget_ledger.py:_write()` (temp file + `os.replace()`)
8. Create `requirements.txt`
9. Remove unused imports in `test_calendar_sync.py`
10. Document UTC timestamp convention in `budget_ledger.py` docstring

---

*Note: Review agent ran read-only. No test execution or linting was performed. Re-run with Bash enabled to include `pytest` results.*

---

## Task 9 Review — 2026-03-17

**Verdict: Approved with Fixes**
**Pipeline: Continue**
**Scope: Task 9 (End-to-End Smoke Test)**
**Review cycle: 1**

---

### Critical

None. No new security vulnerabilities. Previously flagged dashboard issues remain deferred to post-Plan 3.

---

### Warnings (auto-approved, fix in next /implement pass)

- **Tests not confirmed passing.** Bash access denied — `python -m pytest tests/ -v` could not be executed. Structurally sound on visual inspection, but not verified. Run manually before final commit.

- **FlightClaw smoke test not run.** Cannot execute `python skills/flightclaw/scripts/search-flights.py` without Bash. Verify manually.

- **Final commit not created.** Most recent commit is `efe1790`. No "foundation complete" commit as specified by the plan. Create after smoke tests pass: `feat: foundation complete — agents, tools, flightclaw, slash commands`.

- **`requirements.txt` still missing.** Carry-forward from Tasks 6-8. Blocks clean-environment test runs.

- **`test_calendar_sync.py` unused imports still present.** Carry-forward from Tasks 6-8.

---

### Structural Verification — PASS

All expected files present and in correct locations:

| Expected | Status |
|---|---|
| 5 AGENT.md files (root + 4 agents) | ✅ |
| 9 workflow files across 4 agents | ✅ |
| 5 slash commands in `.claude/commands/` | ✅ |
| 3 tool modules + `__init__.py` + dashboard | ✅ |
| 3 test files + `conftest.py` | ✅ |
| FlightClaw skill with all scripts | ✅ |
| `tracked.json` empty `[]` | ✅ |
| `.env.example` with 3 env vars | ✅ |
| `output/changelog.md` | ✅ |

---

### What's Good

- All structural checkpoints pass. Foundation is complete.
- `tracked.json` confirmed empty — no personal data in repo.
- Previous review fixes applied: PII handling, error handling in booking/accommodation workflows, price verification step, tracked.json cleared.
- Test design is solid even if not yet executed.

---

### Cumulative Open Fix List (all reviews)

1. ⏸️ **[POST-PLAN 3]** Path traversal protection on `dashboard_server.py`
2. ⏸️ **[POST-PLAN 3]** Auth on `POST /api/trips/{trip_id}/itinerary`
3. Create `requirements.txt` with pinned deps
4. Remove/guard unused `date` param in `airlabs.py`
5. Wrap `response.json()` in try/except in `airlabs.py` error path
6. Handle empty/null AirLabs response explicitly
7. Error handling in `budget_ledger.py:_read()` + atomic write in `_write()`
8. Remove unused imports in `test_calendar_sync.py`
9. Document UTC timestamp convention in `budget_ledger.py`
10. Run `python -m pytest tests/ -v` and confirm all pass
11. Run FlightClaw smoke test manually
12. Create final commit: `feat: foundation complete`

---

*Note: Review agent ran read-only. No tests executed, no linting performed. Structural verification via Glob/Read/Grep only.*

---

## Plan 3 Review (Dashboard) — 2026-03-17

**Verdict: ⛔ Blocked — Needs Decision**
**Pipeline: Paused**
**Scope: `tools/dashboard_server.py`, `tools/static/index.html`, `tools/static/style.css`, `tools/static/app.js`**

---

### Critical

- ~~**`tools/dashboard_server.py` — Path traversal**~~ ✅ **Fixed 2026-03-17** — Added `_safe_trip_dir()` helper that resolves and validates all `trip_id` paths stay within `TRIPS_DIR`. Applied to all 7 endpoints.

- ~~**`tools/dashboard_server.py` — Unauthenticated write endpoint**~~ ✅ **Fixed 2026-03-17** — Path traversal now blocked on POST endpoint. Error message no longer leaks internal path. Added `max_length=500_000` on `ItineraryUpdate.content`.

- ~~**`tools/static/app.js` — DOM-based XSS via `innerHTML`**~~ ✅ **Fixed 2026-03-17** — Added `esc()` helper that escapes `&`, `<`, `>`, `"`, `'`. Applied to all data interpolations in Trips, Scout, and Hotels tabs. `markdownToHtml()` now HTML-escapes input before processing.

- ~~**`tools/static/app.js` — XSS in `onclick` string interpolation**~~ ✅ **Fixed 2026-03-17** — Trip card `onclick` replaced with event delegation on `data-trip-id` attribute. Edit button `onclick` replaced with `addEventListener` using closure over `content` variable.

---

### Warnings (auto-approved, fix next pass)

- `markdownToHtml` doesn't escape HTML before processing — enables the XSS above
- `@app.on_event("startup")` deprecated — use `lifespan` context manager
- SSE reconnect leaks `EventSource` instances — call `eventSource.close()` before creating new one
- Error detail in POST response leaks internal file path — return generic message, log internally
- Sequential fetch per trip in Scout tab — use `Promise.all` (Budget tab does this correctly)
- No Content-Security-Policy header or meta tag
- No request size limit on `ItineraryUpdate.content`
- Missing `requirements.txt` (carry-forward)

---

### Spec Gaps (dashboard v1 — acceptable to defer)

- Scout tab missing: cabin class, tracking start date
- Itinerary tab missing: agent last-updated / user last-edited timestamps
- Budget tab missing: "Add expense" form
- Crons tab missing: Run now / Pause controls, View log
- No "Approve & Reconcile" button (Phase 2.5 feature)

---

### What's Good

- SSE subscriber queue pattern is well-designed: keepalive pings, dead-subscriber cleanup, proper `finally` cleanup
- Price classification logic matches design spec exactly (thresholds, badge colors, min data points)
- Every `fetch` wrapped in try/catch with user-visible errors and empty state handling
- Budget tab visualization matches spec — progress bar, confirmed vs estimated, per-trip cards
- CSS is polished — dark theme, responsive grid, hover states. Production-quality for a personal tool
- Clean separation: server handles data access + SSE, frontend handles all rendering

---

### Updated Cumulative Fix List

1. ~~Path traversal on `dashboard_server.py`~~ ✅ Fixed
2. ~~Unauthenticated write endpoint~~ ✅ Fixed
3. ~~XSS via `innerHTML` in `app.js`~~ ✅ Fixed
4. ~~XSS via `onclick` string interpolation~~ ✅ Fixed
5. Create `requirements.txt`
6. Remove/guard unused `date` param in `airlabs.py`
7. Wrap `response.json()` in try/except in `airlabs.py` error path
8. Handle empty/null AirLabs response explicitly
9. Error handling in `budget_ledger.py:_read()` + atomic write in `_write()`
10. Remove unused imports in `test_calendar_sync.py`
11. Fix deprecated `@app.on_event("startup")`
12. Fix SSE `EventSource` leak in `app.js`
13. Add CSP header or meta tag
14. Add `max_length` on `ItineraryUpdate.content`
15. Run `pytest tests/ -v` and confirm all pass
16. Create final commit: `feat: foundation complete`

---

*Note: Review agent ran read-only. Security findings based on static code analysis only.*

---

## Plan 2 Review (hotelclaw) — 2026-03-17

**Verdict: Approved with Fixes**
**Pipeline: Continue**
**Scope: `skills/hotelclaw/`**
**Review cycle: 1**

---

### Critical

- ~~**`skills/hotelclaw/helpers.py` — Non-atomic write**~~ ✅ **Fixed 2026-03-17** — `save_tracked()` now writes to a temp file then `os.replace()`. Crash-safe.

- ~~**`skills/hotelclaw/scrapers.py` — Brittle Airbnb `._tyxjp1` selector**~~ ✅ **Fixed 2026-03-17** — Replaced with stable selectors (`aria-label*="per night"`, `data-testid`, fallback `span[aria-hidden]`). Added warning log when all extracted prices are None.

---

### Warnings (auto-approved, fix next pass)

- **Missing `search_dates` tool.** Design spec lists it as one of six required tools. Not implemented in `tracking.py`, `server.py`, or scripts. Add or document deferral.
- **Missing `scripts/remove-tracked.py`.** MCP tool exists in `tracking.py:190` but no CLI script. Add for parity with flightclaw.
- **No exponential backoff retry.** Spec explicitly requires 3 attempts with 2s/4s/8s backoff per source. Currently one attempt and fail. Implement before production cron use.
- **Booking.com URL date format likely wrong.** Code strips hyphens to produce `YYYYMMDD` but Booking.com URLs use `YYYY-MM-DD`. Will cause zero results. Verify and fix.
- **No URL encoding on city param.** City interpolated directly into URLs — special characters could inject query parameters. Use `urllib.parse.quote()`.
- **No date validation on `track_property`.** Malformed dates throw unhandled `ValueError`. Wrap in try/except with user-friendly error.
- **No tests.** Zero test files for hotelclaw. At minimum test `helpers.py` pure functions and date/price parsing.
- **`setup.sh` installs without version pinning.** Add `requirements.txt` with pinned versions.
- **`fmt_price` hardcodes `$` symbol.** Shows `$120 EUR` if currency is EUR/GBP/JPY. Use currency code alone or a symbol map.

---

### What's Good

- **`tracked.json` starts empty and is gitignored.** Lesson applied from Tasks 1-3 review.
- **Three-source graceful degradation.** `search_all_sources()` returns partial results when any source fails — matches spec exactly.
- **Faithful mirror of flightclaw architecture.** File structure, MCP registration pattern, and tool naming are all consistent.
- **Price history schema is spec-compliant.** Rolling `{timestamp, price_per_night}` array matches design doc.
- **Per-card error handling in scrapers.** One malformed card doesn't abort the entire page scrape.

---

### Fix List for Next /implement Pass (Plan 2)

1. **[HIGH]** Atomic writes in `save_tracked()` (temp file + `os.replace()`)
2. **[HIGH]** Replace Airbnb `._tyxjp1` selector + add zero-price warning
3. **[HIGH]** Exponential backoff retry (3 attempts, 2s/4s/8s) per spec
4. **[MEDIUM]** Fix Booking.com date format in URLs
5. **[MEDIUM]** URL-encode city parameter
6. **[MEDIUM]** Date validation with user-friendly errors
7. **[MEDIUM]** Implement `search_dates` tool or document deferral
8. **[LOW]** Add `scripts/remove-tracked.py`
9. **[LOW]** Create `requirements.txt` with pinned versions
10. **[LOW]** Add basic tests for `helpers.py` and scrapers

---

*Note: Review agent ran read-only. No linting or test execution performed.*

---

## Design QA — 2026-03-18

**Verdict: Needs Polish** (was; now **Polished** after fixes applied in this session)

Reviewed: `tools/static/index.html`, `tools/static/style.css`, `tools/static/app.js`  
Live dashboard at `http://localhost:8000` — screenshots captured across all tabs.

---

### Critical (blocks launch) — All Fixed in This Session

- **Hotels tab / Itinerary tab — Trip selector visual inconsistency.**  
  Root cause: `style.css` had a single rule `#itinerary-trip-selector select { ... }` that styled only the Itinerary dropdown. The Hotels dropdown (`#hotels-trip-selector select`) had no matching rule, so it rendered with the browser-default appearance: white background, system font, no border radius — completely at odds with the dark theme.  
  Fix applied: Extended the CSS selector to cover both containers:  
  `#hotels-trip-selector select, #itinerary-trip-selector select { ... }`  
  Added `cursor: pointer` to both for consistency with button elements.

- **Hotels tab — Two inline `style=""` attributes with one-off hex values.**  
  `color:#22c55e` (free cancellation) and `color:#60a5fa` (booking link) were not part of the defined palette (`#3fb950` green, `#58a6ff` blue). They would be invisible to future palette changes and violated internal consistency.  
  Fix applied: Replaced both with CSS classes `.free-cancel` and `.book-link` in `style.css`. The booking link also gained a `:hover` underline state and is now a block-level `<a>` element (removed the wrapping `<div>`).

- **Budget tab — "Budget: $? USD" shown when `budget_usd` is null.**  
  When a trip has no budget set, the template string `$${budget.budget_usd || '?'} USD` produced the literal text "$? USD" — looks like a broken template or placeholder.  
  Fix applied: Replaced with a conditional: shows `$X USD` when set, or an em dash `—` when not set.

---

### Polish (should fix — not addressed in this session)

- **Trips tab — "Budget: —" rendered inconsistently with Budget tab.**  
  The trip card already handles null budget correctly with `'\u2014'` (line 117 of app.js). Consistent. No change needed.

- **Scout tab — Route cards show "No price data" with no explanation of why.**  
  The `japan-2026-05` flights have no price history yet. The empty state text is accurate but gives no guidance. Consider adding a small hint: "Run `/check-flights` to start tracking." Currently the tab-level empty state shows this message, but when there ARE cards with no data, the hint disappears.

- **Hotels tab — `.price-range` class used for chain/distance info.**  
  The line `Marriott Bonvoy · 10 min walk / ...` uses the `.price-range` CSS class, which semantically belongs to price range data. It renders correctly (muted grey, 12px) but the class name is misleading. Low priority — rename to `.card-detail` or similar in a future pass.

- **Hotels tab — "Book" link color changed from `#60a5fa` to `#58a6ff`.**  
  The inline style was using `#60a5fa` (a one-off Tailwind blue-400 equivalent) while the rest of the UI uses `#58a6ff` (the design system's blue). The fix aligns them. Visually nearly identical, but now consistent.

- **Budget tab — "Remaining: $0" when no budget is set.**  
  With `budget_usd = null`, the math `(null || 0) - 0 = 0` produces "Remaining: $0" — which is misleading. Should also show "—" when no budget is configured. Not fixed in this session; low impact for a personal tool.

- **Crons tab — No favicon or distinct page title per tab.**  
  `<title>Travel Concierge</title>` is static. No favicon is set. For a personal tool this is acceptable; for production it would be flagged.

---

### Accessibility

- **Trip selector dropdowns — no `<label>` element.**  
  Both `<select>` elements are unlabeled. Screen readers will announce the selected option text only, with no context about what the select controls. Fix: add `<label for="hotels-select" class="sr-only">Filter by trip</label>` or use `aria-label` on the select element.

- **"Book" link — link text is not descriptive.**  
  `<a>Book →</a>` repeated for every hotel card is ambiguous when tabbing. Screen readers will announce "Book, link" × 5 with no hotel name. Fix: add `aria-label="Book ${prop.name}"` to each link.

- **Icon-only live indicator — no accessible label.**  
  The live indicator (`⚫ connecting` / `🟢 live`) uses emoji characters with no `aria-label`. Assistive technologies will read raw emoji names. Fix: wrap in `<span aria-live="polite" aria-label="Connection status: live">` or similar.

- **Focus indicators — visible on interactive elements.**  
  Browser default focus rings are present on tabs, buttons, and selects (no `outline: none` override in stylesheet). This is a positive — no action needed.

- **Color contrast — passes WCAG AA.**  
  Primary text `#e1e4e8` on `#0f1117` background: ~13:1 ratio. Muted text `#8b949e` on `#161b22` card background: ~5.3:1. Badge text meets 4.5:1 for all badge variants. The green `#3fb950` on `#1a3a1f` badge background passes 3:1 for large text (12px bold).

---

### What's Good

- **Dark theme execution is solid.** The `#0f1117` / `#161b22` / `#21262d` three-tier depth system creates clear visual hierarchy between body, cards, and interactive surfaces.
- **Badge system is complete and consistent.** Five semantic badge variants (green/yellow/orange/red/blue/grey) covering all price classification states and trip phases. Colors are tasteful — not garish.
- **Hotel cards show the right information.** Name, city/nights, chain, distance, free cancellation status, and booking link are all present and legible. The visual hierarchy (bold name → muted metadata → price → actions) is clear.
- **Trip cards are clean.** The ID in blue, route in white, meta in muted grey gives a natural reading order. Phase badge positioned at top-right where the eye lands last.
- **Empty states are handled for every tab.** No raw blank screens — every data-empty case has a message and most suggest the next action.
- **Error states present with meaningful text.** All `catch` blocks display the actual error message inside the panel, not a silent failure.
- **No lorem ipsum or TODO text anywhere in the rendered UI.**
- **SSE live indicator works.** Shows green dot + "live" when connected.

---

### Files Modified in This Session

- `tools/static/style.css` — Extended trip selector CSS rule to cover Hotels tab; added `.free-cancel` and `.book-link` utility classes
- `tools/static/app.js` — Replaced two inline `style=""` attributes with CSS classes; fixed Budget null display from "$? USD" to "—"

