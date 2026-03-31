# Workflow: Book and Confirm

## Purpose
Navigate a booking flow for accommodation, dining, or activity reservations. Verify details, stop at the guest details or confirmation page, and wait for the user to complete the booking. For phone-only venues, use Vapi (Method B). For Bangkok restaurants on Chope, use Method C (fully automated end-to-end).

## Input
User specifies what to book (e.g. "book the Shinjuku Granbell for Japan trip", "reserve dinner at Narisawa on 16 May", "get tickets to [event]", "call Yoshitake to check availability").

## Execution Rules

**Always use absolute paths when invoking scripts.** Never use `cd && python` — use the full path directly:
```bash
# Correct
~/.pyenv/shims/python "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge/tools/script.py"
~/.pyenv/shims/python "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge/.tmp/script.py" > /tmp/script.log 2>&1

# Wrong — triggers approval prompt
cd "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge" && python .tmp/script.py > /tmp/log 2>&1
```

This applies to all generated scripts in `.tmp/` and all calls to `tools/`.

---

## Method A — Browser Booking

### For Accommodation
1. Read `trips/[trip-id]/accommodation.json` — find the selected property
2. Open the booking site — prefer direct hotel site (Marriott, Hyatt) over OTAs; fall back to Booking.com or Trip.com if direct site has no availability
3. Navigate to the specific property and dates
4. Verify the following match what's in accommodation.json — alert user if anything differs by more than 10%:
   - Check-in / check-out dates
   - Number of guests
   - Room type
   - Total price
5. Confirm cancellation policy and prepayment vs pay-at-hotel — surface this to the user
6. Navigate to the guest details page
7. Fill in name and phone number if the form requires them
8. Screenshot the page and save to `trips/[trip-id]/confirmations/[property]-prefill.png`
9. **STOP HERE** — display a summary to the user:
   ```
   Ready to book:
   [Property name]  [City]
   Check-in: [date]  Check-out: [date]  [N] nights
   Room: [type]  Cancellation: [policy]  Payment: [prepay / at hotel]
   Price: $[X] USD

   Please review and complete the booking yourself.
   Let me know when done and share the confirmation number + final price paid.
   ```
10. Wait for user to confirm they completed the booking
11. Ask user for: confirmation number, final price paid
12. Screenshot the confirmation page and save to `trips/[trip-id]/confirmations/[property]-confirmed.png`
13. Update `trips/[trip-id]/accommodation.json`:
    - Set `"booked": true` on the selected property
    - Set `"confirmed_price": [price]`
    - Set `"confirmation_number": "[number]"`
14. Call `tools/budget_ledger.py`:
    ```python
    add_item(trip_id, "accommodation", "[Property name] [City]", [price], "confirmed")
    ```
15. Draft confirmation email via Gmail MCP:
    - Subject: "Hotel Confirmed: [Property name] [City] [check-in date]"
    - Include: confirmation number, dates, price, cancellation policy
16. Add to Google Calendar via Google Calendar MCP:
    - Event: "🏨 [Property name]"
    - Start: check-in date, End: check-out date (Asia/Hong_Kong timezone)
    - Description: confirmation number, address, cancellation policy

### For Dining / Events
1. Find the restaurant or event details (URL, date, time, party size)
2. Navigate to the reservation or ticketing page — prefer TableCheck or direct site for Japanese restaurants
3. Fill in name, phone number, and party size / ticket quantity
4. Screenshot the page before submitting
5. **STOP HERE** — display a summary:
   ```
   Ready to reserve:
   [Name]  [Date]  [Time]  [Party size / tickets]
   Price: $[X] (if applicable)

   Please review and complete the booking yourself.
   Let me know when done.
   ```
6. Wait for user confirmation
7. Screenshot the confirmation page and save to `trips/[trip-id]/confirmations/[venue]-confirmed.png`
8. If there is a cost, call `tools/budget_ledger.py` to add to budget.json
9. Add to Google Calendar via Google Calendar MCP (Asia/Hong_Kong timezone)

---

## Method B — Phone Booking (Vapi)

Use when: venue has no online booking, or is phone-only. Common for ryokans, omakase counters, and small restaurants in Japan.

### Step 1: Prepare call script
Generate a natural-language script in the appropriate language (English or Japanese).
For Japanese venues, write the script in Japanese. The script must include:
- Greeting and who you represent: "I'm calling on behalf of Mr. Yier..."
- Specific request: date, time, party size, room type, special requests
- Confirmation of availability
- Any deposit or payment method questions

Save script to `.tmp/vapi-script-{venue}.txt`

### Step 2: Make the call
```bash
~/.pyenv/shims/python "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge/tools/vapi_call.py" \
  --to "+[venue phone number]" \
  --language "ja" \
  --script-file "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge/.tmp/vapi-script-{venue}.txt" \
  --purpose "restaurant reservation" \
  --output "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge/trips/[trip-id]/confirmations/call-{venue}-{date}.json"
```

### Step 3: Review transcript
After the call completes, read the output JSON. Extract:
- Was reservation confirmed? Y/N
- Confirmation number or name held under
- Any conditions (deposit required, dietary questions, etc.)

### Step 4: Report to Yier
```
📞 CALL RESULT — [Venue]
  Status:   ✅ Confirmed / ❌ Not available / ⚠️ Needs follow-up
  Held as:  [name]
  Ref:      [confirmation code if given]
  Notes:    [any conditions or follow-ups needed]
  [Transcript snippet]
```

### Step 5: Update state files (if confirmed)
- If accommodation: update `trips/[trip-id]/accommodation.json` with `booked: true`, confirmation details
- Call `tools/budget_ledger.py` if a cost was confirmed
- Add to Google Calendar via Google Calendar MCP (Asia/Hong_Kong timezone)
- Draft confirmation summary email via Gmail MCP (do not send without instruction)

---

---

## Method C — Chope Booking (Bangkok restaurants, fully automated)

Use when: restaurant is listed on Chope (`www.chope.co/bangkok-restaurants`). This method completes the booking end-to-end and returns the confirmation ID.

### Prerequisites
- `CHOPE_USERNAME` and `CHOPE_PASSWORD` in `.env`
- `playwright` installed (`pip install playwright && playwright install chromium`)
- Reusable script: `scripts/chope_book.py`

### Step 1: Find the restaurant's Chope details
You need two identifiers:
- **slug**: the URL path segment (e.g. `plu-bangkok`) — find by searching `https://www.chope.co/bangkok-restaurants/list_of_restaurants` or the restaurant page URL
- **rid**: the Chope restaurant ID (e.g. `plu1909bkk`) — visible in the booking widget URL once you open it

To find both, load the restaurant page and inspect the `#btn_sub` form's POST target URL, or check `.tmp/` for any prior booking data.

### Step 2: Confirm available time slots
Plu lunch runs 11am–1:45pm. The last lunch slot is **1:45pm** (not 2pm). Dinner from 5pm. Always verify available slots match the user's request before running the script. If the requested time isn't available, surface the nearest slot and confirm.

### Step 3: Run the booking script
```bash
~/.pyenv/shims/python "/Users/yiercao/Vibe_Coding/AgenticWorflow_Travel Concierge/scripts/chope_book.py" \
  --rid plu1909bkk \
  --slug plu-bangkok \
  --date 2026-03-30 \
  --time "1:45 pm" \
  --adults 3
```

Or call `book()` directly from a Python script/tool.

### Step 4: On success — post-booking actions
The script returns a dict with `confirmation_id`, `date`, `time`, `adults`, `screenshot`.

1. **Add to Google Calendar** via Google Calendar MCP:
   - Event: `🍽️ Lunch/Dinner — [Restaurant Name]`
   - Start/End: use Bangkok timezone `Asia/Bangkok` (UTC+7)
   - Description: confirmation ID, address, phone
   - Reminder: 60 min popup

2. **Report to user:**
   ```
   ✅ [Restaurant] — confirmed
   📅 [Day] [Date], [Time]
   👥 [N] adults
   🔖 Confirmation ID: [ID]
   Added to Google Calendar.
   ```

3. **Update trip state files** (if part of a trip):
   - Add dining entry to `trips/[trip-id]/itinerary.md`
   - Call `tools/budget_ledger.py` if there's a cover charge or prix-fixe cost

### How the Chope widget flow works (technical reference)
```
1. Login → www.chope.co/bangkok-restaurants/user
2. Open restaurant page with pre-filled params:
   ?children=0&adults=N&date=YYYY-MM-DD&time=H%3AMM+pm
3. Click #btn_sub (form POSTs to book.chope.co, opens popup tab target="_blank")
4. Popup: booking.chope.co/widget/#/booking_index?...
   a. Click "Select Date" button → calendar opens
   b. Click .vc-day.id-YYYY-MM-DD → .vc-focusable to select day
   c. Click .time_item div with matching text (exact match, e.g. "1:45 pm")
   d. Click "Next" → Contact Details page
5. Contact Details page:
   - Form is pre-filled from account (name, email, phone)
   - Check .nav-confirmation-row input[type='checkbox'] (T&C — REQUIRED)
   - Click "Book table" (enabled after T&C checked)
6. Confirmation: URL contains /booking_confirmation/{ID}
```

**Key gotchas:**
- `"2:00 pm" in "12:00 pm"` is True (substring) — always use exact match for time slots
- "Book table" button is disabled until the T&C checkbox is clicked
- The popup is captured via `context.on("page", ...)` listener — must set up before clicking #btn_sub
- The contact form has a "Save" button (for editing name inline) — don't click that, click "Book table"

---

## Error Handling
- **Site unreachable or no longer available:** Abort. Notify user: "Unable to reach [site] / [item] is no longer available. Please check manually."
- **Price change >10%:** Stop and alert user before proceeding. Do not continue without explicit go-ahead.
- **Login required:** Ask user to log in, then continue from where you paused.
- **Browser automation blocked:** Switch to manual mode — describe each step to the user and wait for them to complete it.
- **Vapi call fails or goes unanswered:** Notify user. Suggest retry at a different time or manual call.
- **Vapi call result is ambiguous (⚠️ Needs follow-up):** Do not update state files. Surface transcript to user and ask how to proceed.
- **Booking fails partway through:** Notify user immediately. No state files have been modified at this point, so nothing needs to be rolled back.
