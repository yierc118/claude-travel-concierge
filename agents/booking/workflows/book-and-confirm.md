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
