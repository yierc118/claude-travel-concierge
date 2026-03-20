#!/usr/bin/env python3
"""
Cron script: check accommodation prices for all active trips every 12h.
Usage: python tools/monitor_hotels.py
Cron:  0 */12 * * * ~/.pyenv/shims/python /path/to/tools/monitor_hotels.py
"""

import anyio
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, SystemMessage

PROJECT_ROOT = Path(__file__).parent.parent


async def run():
    prompt = (
        "You are the Accommodation subagent. Run the hotel price monitoring workflow. "
        "Follow the steps in agents/accommodation/workflows/monitor-prices.md exactly. "
        "Work autonomously — check all active trips, update accommodation.json files, "
        "log alerts to STATUS.md, and log the run to output/changelog.md."
    )

    print(f"[monitor_hotels] Starting accommodation price check...")

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
            print(f"[monitor_hotels] Session: {msg.data.get('session_id', 'unknown')}")
        elif isinstance(msg, ResultMessage):
            print(f"[monitor_hotels] Done: {msg.result[:200]}")
            print(f"[monitor_hotels] Stop reason: {msg.stop_reason}")


if __name__ == "__main__":
    anyio.run(run)
