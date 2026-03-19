# Workflow: Book and Confirm

## Purpose
Navigate a booking flow for accommodation, dining, or activity reservations. Verify details, stop at the guest details or confirmation page, and wait for the user to complete the booking. For phone-only venues, use Vapi (Method B).

## Input
User specifies what to book (e.g. "book the Shinjuku Granbell for Japan trip", "reserve dinner at Narisawa on 16 May", "get tickets to [event]", "call Yoshitake to check availability").

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
python3 tools/vapi_call.py \
  --to "+[venue phone number]" \
  --language "ja" \
  --script-file .tmp/vapi-script-{venue}.txt \
  --purpose "restaurant reservation" \
  --output trips/[trip-id]/confirmations/call-{venue}-{date}.json
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

## Error Handling
- **Site unreachable or no longer available:** Abort. Notify user: "Unable to reach [site] / [item] is no longer available. Please check manually."
- **Price change >10%:** Stop and alert user before proceeding. Do not continue without explicit go-ahead.
- **Login required:** Ask user to log in, then continue from where you paused.
- **Browser automation blocked:** Switch to manual mode — describe each step to the user and wait for them to complete it.
- **Vapi call fails or goes unanswered:** Notify user. Suggest retry at a different time or manual call.
- **Vapi call result is ambiguous (⚠️ Needs follow-up):** Do not update state files. Surface transcript to user and ask how to proceed.
- **Booking fails partway through:** Notify user immediately. No state files have been modified at this point, so nothing needs to be rolled back.
