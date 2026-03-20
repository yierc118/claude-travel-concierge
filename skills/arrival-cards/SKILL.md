---
name: arrival-cards
description: Country-specific arrival card knowledge — portal URLs, required fields, timing windows, and field mappings from skeleton.json and yier-preferences.md. Covers Singapore, Japan, Thailand, UK, and common destinations. Tells the agent exactly what to fill in where, and when to submit. Does NOT auto-submit (most portals are CAPTCHA-gated).
status: scaffold — not yet implemented
---

# arrival-cards

Pre-fill arrival cards for destinations in the trip itinerary. Maps trip data (passport, flight number, accommodation address) to the specific fields each country's portal requires. Surfaces the portal URL and a pre-filled field list for the user to copy-paste or complete.

> **Scope:** Knowledge layer only — field mappings, portal URLs, timing rules, and gotchas. Does NOT submit forms automatically. Most government arrival card portals are CAPTCHA-gated or session-protected.

---

## When to invoke

Invoke this skill when:
- Phase 4 is active AND departure is within 14 days
- User asks "do I need to fill in an arrival card for X?"
- STATUS.md has a pending action: `arrival_card_due`

---

## Inputs

Read from these files before applying this skill:

| Source | Fields used |
|--------|------------|
| `trips/[trip-id]/skeleton.json` | cities (name, country, arrive, depart), legs (flight number, date), travellers |
| `trips/[trip-id]/flights.json` | confirmed flight number, airline, arrival time |
| `trips/[trip-id]/accommodation.json` | confirmed hotel name + address per city |
| `reference/yier-preferences.md` | passport details, nationality, address in home country |

---

## Country Reference

### 🇸🇬 Singapore — SG Arrival Card (SGAC)

| Field | Value source |
|-------|-------------|
| Portal | https://eservices.ica.gov.sg/sgarrivalcard/ |
| App | MyICA Mobile |
| Submit window | Up to 3 days before arrival (not earlier) |
| Cost | Free |
| **Full name** | `yier-preferences.md` → passport name |
| **Passport number** | `yier-preferences.md` → passport number |
| **Nationality** | `yier-preferences.md` → nationality |
| **Date of birth** | `yier-preferences.md` → DOB |
| **Flight number** | `flights.json` → confirmed flight number for SIN leg |
| **Accommodation address** | `accommodation.json` → confirmed hotel address, Singapore |
| **Departure date from SG** | `skeleton.json` → cities[Singapore].depart |

**Gotchas:**
- Submission window is strict: too early = form not available; too late = process at counter
- Submission is per person — if travelling with others, each needs separate submission
- Confirmation is emailed + visible in MyICA app; screenshot it

---

### 🇯🇵 Japan — Visit Japan Web (VJW)

| Field | Value source |
|-------|-------------|
| Portal | https://vjw-lp.digital.go.jp/en/ |
| Submit window | Any time before arrival (register account first) |
| Cost | Free |

**Critical:** Japan has TWO separate submissions on VJW — both required:
1. **Immigration (Landing Permission)** — generates QR code for immigration counter
2. **Customs Declaration** — generates QR code for customs counter

Both QR codes are shown on your phone at the respective counters.

| Field | Immigration | Customs | Source |
|-------|------------|---------|--------|
| Full name | ✓ | ✓ | `yier-preferences.md` |
| Passport number | ✓ | ✓ | `yier-preferences.md` |
| Nationality | ✓ | – | `yier-preferences.md` |
| Flight number | ✓ | – | `flights.json` → Japan leg |
| Accommodation address (first night) | ✓ | – | `accommodation.json` → Japan, first city |
| Carrying cash >¥1M or prohibited items | – | ✓ | Usually "No" |

**Gotchas:**
- VJW account must be created before trip — takes ~5 minutes; recommend doing it in Phase 3
- QR codes expire if you regenerate them — screenshot before landing
- As of 2025, VJW is optional (paper form available at airport) but faster

---

### 🇹🇭 Thailand — Thailand Pass / TM6

| Field | Value source |
|-------|-------------|
| Portal | Arrival card is paper (TM6) — distributed on the plane or at immigration |
| Submit window | Fill on the plane or at the airport |
| Cost | Free |
| Digital option | None (as of 2025) |

| Field | Value | Source |
|-------|-------|--------|
| Full name | | `yier-preferences.md` |
| Passport number | | `yier-preferences.md` |
| Nationality | | `yier-preferences.md` |
| Flight number | | `flights.json` → BKK/DMK leg |
| Accommodation name | | `accommodation.json` → Bangkok |
| Accommodation address | | `accommodation.json` → Bangkok confirmed hotel address |
| Purpose of visit | Tourism | — |
| Length of stay | days in Thailand | `skeleton.json` → cities[Bangkok].nights |

**Gotchas:**
- TM6 is a paper form — prep the data in advance to fill quickly on the plane
- Keep the departure card (TM6 bottom half) — it's collected when you leave Thailand

---

### 🇬🇧 United Kingdom — UK ETIAS (not yet in force) / ETA

| Field | Value source |
|-------|-------------|
| Portal | https://apply.eta.homeoffice.gov.uk/ |
| Submit window | Anytime before travel; apply ≥72h before departure |
| Cost | £10 per person |
| Valid | 2 years or until passport expires |

| Field | Value | Source |
|-------|-------|--------|
| Full name | | `yier-preferences.md` |
| Passport number | | `yier-preferences.md` |
| Nationality | | `yier-preferences.md` |
| Date of birth | | `yier-preferences.md` |
| Email | | `yier-preferences.md` |

**Gotchas:**
- UK ETA is a visa-like pre-clearance — not a traditional arrival card
- Required for Hong Kong passport holders as of 2025 — check current requirements before assuming exempt
- Usually approved instantly; occasionally takes up to 3 days

---

### 🇦🇺 Australia — Australian Travel Declaration (ATD) / incoming passenger card

| Field | Value source |
|-------|-------------|
| Portal | https://atd.homeaffairs.gov.au/ |
| App | Australian Travel Declaration app |
| Submit window | Up to 72h before arrival |
| Cost | Free |

| Field | Value | Source |
|-------|-------|--------|
| Full name | | `yier-preferences.md` |
| Passport number | | `yier-preferences.md` |
| Nationality | | `yier-preferences.md` |
| Flight number | | `flights.json` → Australia leg |
| Accommodation address | | `accommodation.json` → Australia |
| Goods to declare | Usually "No" | — |

---

## Output format

When this skill is applied, output a pre-fill checklist for the user:

```
## Arrival Card — [Country] ([City])
Portal: [URL]
Submit by: [date — calculated from arrival date and submission window]

Fields to fill:
- Full name: [value from yier-preferences.md]
- Passport number: [value — remind user to check .env or preferences file]
- Flight number: [value from flights.json]
- Hotel name: [value from accommodation.json]
- Hotel address: [value from accommodation.json]
- [any country-specific fields]

Gotchas:
- [country-specific warnings from reference above]
```

---

## Adding new countries

When a trip includes a country not listed here, research the arrival card requirement and add a new section following the format above. Check:
1. Is there a digital portal or is it paper-only?
2. What is the submission window?
3. What fields are required?
4. What are the common gotchas for this country?

Update this file and log the addition to `output/changelog.md`.

---

## Implementation roadmap

When ready to build:

1. **Phase 1 (current — scaffold):** Skill file only. Agent reads this file and manually assembles the pre-fill checklist for the user.
2. **Phase 2:** `scripts/check-required.py` — scans `skeleton.json` for countries, returns list of required arrival cards + deadlines. Add a STATUS.md `arrival_card_due` action when deadline is within 14 days.
3. **Phase 3:** `scripts/prefill.py` — reads trip files + this skill's country table, generates a formatted pre-fill checklist and saves to `trips/[trip-id]/arrival-cards/[country].md`.
4. **Phase 4 (stretch):** Playwright automation for portals that allow it (Singapore ICA is most likely candidate — simpler form, no CAPTCHA on initial load). Pause + screenshot before final submission.
