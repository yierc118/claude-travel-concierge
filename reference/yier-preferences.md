# Yier's Travel Preferences

Reference file loaded by Scout and Accommodation agents at the start of every search.
Sensitive account numbers are stored in `.env` — referenced here by variable name.

---

## Flight Preferences

**Departure window:** No departures before 08:00 (hard rule)

**Stops:**
- Nonstop: strongly preferred (+3 score)
- 1-stop: only if layover is 1–3h; under 1h or over 3h = hard avoid
- `max_layover_hours: 3` / `min_layover_hours: 1`
- Upgrade to nonstop if premium is under 30% more (`prefer_nonstop_if_premium_under: 30%`)

**Airlines:** SQ/CX nice-to-have; cost is priority; mix of full-service and budget depending on route length

**Cabin:** Economy; Flexi fare on return legs (allows changes)

**Seats:** Selects in advance — standard seat in forward zone preferred

### Frequent Flyer Accounts

| Program | Account ID | Status | Notes |
|---|---|---|---|
| Singapore Airlines KrisFlyer | `$KRISFLYER_ID` | Elite Silver (until 31 May 2026) | Needs 3,732 Elite miles to retain — prioritise SQ-earning flights when similarly priced |
| Cathay Pacific AsiaMiles | `$ASIAMILES_ID` | Green member | Secondary preference |

**Tiebreaker:** When flights are similarly priced, prefer whichever earns KrisFlyer miles (Elite Silver retention is priority).

---

## Accommodation Preferences

### Loyalty Programs & Booking Tiers

| Program | Account ID | Status | Notes |
|---|---|---|---|
| Marriott Bonvoy | `$MARRIOTT_ID` | Lifetime Silver | First preference among chains |
| World of Hyatt | `$HYATT_ID` | Explorist | Second preference among chains |
| Trip.com | `$TRIPCOM_ID` | Diamond tier | Use for price comparison |
| Booking.com | `$BOOKINGCOM_ID` | Genius Level 2 | Up to 15% discounts |

### Priority Order
1. Marriott Bonvoy or Hyatt — if reasonably priced and good location
2. Boutique / character — independent hotels, heritage hotels, reputable BnBs or Airbnbs

### What Matters
- **Location first** — walkable to the day's activities
- **Free cancellation** — always prefer when available
- **Quality sleep** — clean, proper shower, non-smoking room (hard avoid: smoking rooms)
- **Food proximity** — morning café + evening restaurant access matters
- Open to hotels and serviced apartments — values character and local feel
- Japan: mixes traditional/retro apartments with practical comfort hotels; private onsen ryokan for Hakone-style stays

### Hard Avoids
- Hostels
- Purely functional chain hotels with no character
- Locations requiring 30+ min transit to the core area
- Smoking rooms

---

## Food & Travel Style

### Food
- Diverse cuisines: Italian, Indian, Chinese hotpot, Western brunch, cocktail bars
- When travelling: local cuisine above all
- Dines at both casual and upscale venues
- Coffee that takes itself seriously
- Markets and food halls — early, before crowds (e.g. Tsukiji before 09:00)
- **Avoids:** tourist traps with queues for mediocre food; conveyor belt sushi when a sushi counter is nearby

### Travel Style
- Travels for events (weddings, conferences, HYROX competitions) + exploration
- Quality experience > saving on the wrong things
- Combination of nature adventures (hiking) + culture
- Walking a neighbourhood properly > ticking sights off a list
- **Avoids:** overpacked itineraries
