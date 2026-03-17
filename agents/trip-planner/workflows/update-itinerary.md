# Workflow: Update Itinerary

## Purpose
Edit the living itinerary document in response to user requests or new information (e.g. a flight time changed, a restaurant closed).

## Steps

1. Read current `trips/[trip-id]/itinerary.md`
2. Read current `trips/[trip-id]/skeleton.json` (for dates and constraints)
3. Understand the requested change
4. Make the edit — preserve all existing sections not being changed
5. Update the footer:
   ```
   Agent last updated: [datetime]
   ```
6. Confirm the change to the user with a brief summary of what changed

## Rules
- Never overwrite the full file — edit the relevant section only
- If the user's edit conflicts with a booking (e.g. they move a day but a hotel is booked), flag the conflict before making the change
- If unsure what the user wants changed, ask before editing
