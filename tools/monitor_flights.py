#!/usr/bin/env python3
"""
Cron script: check flight prices for all active trips every 6h.
Usage: python tools/monitor_flights.py
Cron:  0 */6 * * * ~/.pyenv/shims/python /path/to/tools/monitor_flights.py
"""

import anyio
import sys
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, SystemMessage

PROJECT_ROOT = Path(__file__).parent.parent


async def run():
    prompt = (
        "You are the Scout subagent. Run the flight price monitoring workflow. "
        "Follow the steps in agents/scout/workflows/monitor-prices.md exactly. "
        "Work autonomously — check all active trips, update flights.json files, "
        "log alerts to STATUS.md, and log the run to output/changelog.md."
    )

    print(f"[monitor_flights] Starting flight price check...")

    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            cwd=str(PROJECT_ROOT),
            allowed_tools=["Read", "Write", "Bash", "Glob"],
            permission_mode="acceptEdits",
            setting_sources=["project"],
            max_turns=30,
        ),
    ):
        if isinstance(msg, SystemMessage) and msg.subtype == "init":
            print(f"[monitor_flights] Session: {msg.data.get('session_id', 'unknown')}")
        elif isinstance(msg, ResultMessage):
            print(f"[monitor_flights] Done: {msg.result[:200]}")
            print(f"[monitor_flights] Stop reason: {msg.stop_reason}")


if __name__ == "__main__":
    anyio.run(run)
