#!/usr/bin/env python3
"""
Cron script: send daily price report email at 08:00 HKT.
Usage: python tools/daily_report.py
Cron:  0 0 * * * ~/.pyenv/shims/python /path/to/tools/daily_report.py
       (08:00 HKT = 00:00 UTC)
"""

import anyio
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, SystemMessage

PROJECT_ROOT = Path(__file__).parent.parent


async def run():
    prompt = (
        "Run the daily budget tracking report. "
        "Follow workflows/budget-tracking.md — Daily Report section exactly. "
        "Read all active trips, classify prices, compose and send the email via Gmail MCP, "
        "then update each trip's STATUS.md with 'Last Report' summary."
    )

    print(f"[daily_report] Generating daily travel price report...")

    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            cwd=str(PROJECT_ROOT),
            allowed_tools=["Read", "Write", "Bash", "Glob"],
            permission_mode="acceptEdits",
            setting_sources=["project"],
            max_turns=40,
        ),
    ):
        if isinstance(msg, SystemMessage) and msg.subtype == "init":
            print(f"[daily_report] Session: {msg.data.get('session_id', 'unknown')}")
        elif isinstance(msg, ResultMessage):
            print(f"[daily_report] Done: {msg.result[:200]}")
            print(f"[daily_report] Stop reason: {msg.stop_reason}")


if __name__ == "__main__":
    anyio.run(run)
