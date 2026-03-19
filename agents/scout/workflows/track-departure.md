# Workflow: Track Departure (Cron — every 2h, day-of only)

## Purpose
Monitor booked flights on the day of travel using AirLabs API.

## Activation
This workflow only runs when: a flight entry in `flights.json` has `"booked": true` AND departure date is today.

## Steps

1. Read all `trips/*/flights.json`
2. For each leg where `booked == true`:
   a. Check if `date` == today (Asia/Hong_Kong timezone)
   b. If yes, call AirLabs:
   ```python
   # tools/airlabs.py
   status = get_flight_status(flight_number="SQ321", date="2026-05-14")
   ```
3. Write status to `trips/[id]/STATUS.md`:
   ```
   DEPARTURE [datetime]: SQ321 SIN→NRT — On time, departs 09:45 Gate B12
   ```
   Or if delayed:
   ```
   DEPARTURE ALERT [datetime]: SQ321 delayed. New departure: 11:20 (+95 min). Gate B14.
   ```
4. If delayed by >60 min, compose a Gmail draft (do not auto-send) via Gmail MCP with the delay info

## Notes
- Only runs day-of — the cron is registered with a condition check at the start
- AirLabs costs credits — check `booked == true` before every call
