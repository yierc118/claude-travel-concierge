"""
Vapi outbound call tool — makes phone reservations on behalf of Yier.
Used by the Booking Agent for phone-only venues (ryokans, omakase counters, etc.).

Usage:
    python3 tools/vapi_call.py \
        --to "+813012345678" \
        --language "ja" \
        --script-file ".tmp/vapi-script-yoshitake.txt" \
        --purpose "restaurant reservation" \
        --output "trips/japan-2026-05/confirmations/call-yoshitake-2026-05-16.json"

Required env vars:
    VAPI_API_KEY          — Vapi API key
    VAPI_PHONE_NUMBER_ID  — ID of your Vapi outbound number (+13502029484)

Vapi API docs: https://docs.vapi.ai/api-reference/calls/create
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests


VAPI_BASE_URL = "https://api.vapi.ai"

VOICE_BY_LANGUAGE = {
    "ja": {"provider": "11labs", "voiceId": "pNInz6obpgDQGcFmaJgB"},  # multilingual
    "en": {"provider": "11labs", "voiceId": "EXAVITQu4vr4xnSDxMaL"},  # Rachel
}

POLL_INTERVAL_SECONDS = 10
POLL_TIMEOUT_SECONDS = 600  # 10 minutes max


class VapiError(Exception):
    pass


def _get_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise VapiError(f"{key} environment variable is not set.")
    return value


def _build_assistant_config(script: str, language: str, purpose: str) -> dict:
    """Build an inline Vapi assistant config from the call script."""
    voice = VOICE_BY_LANGUAGE.get(language, VOICE_BY_LANGUAGE["en"])

    system_prompt = f"""You are a polite, professional assistant making a {purpose} on behalf of Mr. Yier Cao.

Follow this script exactly. Do not improvise or go off-script unless the venue asks a clarifying question.
If asked something not covered in the script, apologise and say you will confirm with Mr. Yier and call back.
When the reservation is confirmed or if the venue cannot accommodate, end the call politely.

SCRIPT:
{script}"""

    return {
        "firstMessage": _extract_first_message(script),
        "model": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "messages": [{"role": "system", "content": system_prompt}],
        },
        "voice": voice,
        "endCallPhrases": ["goodbye", "thank you, goodbye", "ありがとうございました", "失礼します"],
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 300,
    }


def _extract_first_message(script: str) -> str:
    """Pull the opening line from the script to use as firstMessage."""
    for line in script.strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return "Hello, I am calling to make a reservation."


def create_call(to_number: str, language: str, script: str, purpose: str) -> str:
    """Initiate an outbound call. Returns the Vapi call ID."""
    api_key = _get_env("VAPI_API_KEY")
    phone_number_id = _get_env("VAPI_PHONE_NUMBER_ID")

    payload = {
        "phoneNumberId": phone_number_id,
        "customer": {"number": to_number},
        "assistant": _build_assistant_config(script, language, purpose),
    }

    response = requests.post(
        f"{VAPI_BASE_URL}/call/phone",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )

    if response.status_code not in (200, 201):
        raise VapiError(f"Vapi API error {response.status_code}: {response.text}")

    call_id = response.json().get("id")
    if not call_id:
        raise VapiError(f"Vapi response missing call ID: {response.text}")

    return call_id


def poll_call_result(call_id: str) -> dict:
    """Poll Vapi until the call ends. Returns the full call result."""
    api_key = _get_env("VAPI_API_KEY")
    elapsed = 0

    print(f"  Call started (ID: {call_id}). Waiting for completion...", flush=True)

    while elapsed < POLL_TIMEOUT_SECONDS:
        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

        response = requests.get(
            f"{VAPI_BASE_URL}/call/{call_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )

        if response.status_code != 200:
            raise VapiError(f"Vapi poll error {response.status_code}: {response.text}")

        call = response.json()
        status = call.get("status", "unknown")
        print(f"  [{elapsed}s] Status: {status}", flush=True)

        if status in ("ended", "failed"):
            return call

    raise VapiError(f"Call timed out after {POLL_TIMEOUT_SECONDS}s — call ID: {call_id}")


def parse_result(call: dict, venue: str, purpose: str) -> dict:
    """Extract reservation outcome from call transcript and metadata."""
    transcript = call.get("transcript", "")
    ended_reason = call.get("endedReason", "unknown")
    duration = call.get("duration", 0)

    # Determine status from ended reason
    if ended_reason in ("assistant-ended-call", "customer-ended-call"):
        status = "completed"
    elif ended_reason in ("customer-did-not-answer", "no-answer"):
        status = "unanswered"
    elif ended_reason == "assistant-error":
        status = "failed"
    else:
        status = "unknown"

    # Extract a short transcript snippet (last 800 chars)
    transcript_snippet = transcript[-800:].strip() if transcript else ""

    return {
        "call_id": call.get("id"),
        "venue": venue,
        "purpose": purpose,
        "status": status,
        "ended_reason": ended_reason,
        "duration_seconds": duration,
        "transcript": transcript,
        "transcript_snippet": transcript_snippet,
        "cost": call.get("cost"),
        "raw": call,
    }


def save_output(result: dict, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def print_summary(result: dict) -> None:
    status_icon = {
        "completed": "✅",
        "unanswered": "❌",
        "failed": "❌",
        "unknown": "⚠️",
    }.get(result["status"], "⚠️")

    print(f"""
📞 CALL RESULT — {result['venue']}
  Status:   {status_icon} {result['status'].upper()} ({result['ended_reason']})
  Duration: {result['duration_seconds']}s
  Cost:     ${result['cost'] or 'n/a'}

  Transcript snippet:
  {result['transcript_snippet'] or '(no transcript)'}
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="Make an outbound Vapi call for a reservation.")
    parser.add_argument("--to", required=True, help="Venue phone number in E.164 format, e.g. +813012345678")
    parser.add_argument("--language", default="en", choices=["en", "ja"], help="Call language (default: en)")
    parser.add_argument("--script-file", required=True, help="Path to the call script .txt file")
    parser.add_argument("--purpose", default="reservation", help="Purpose label, e.g. 'restaurant reservation'")
    parser.add_argument("--output", required=True, help="Path to write the JSON result file")
    parser.add_argument("--venue", default="", help="Venue name for the result summary (inferred from script-file if omitted)")
    args = parser.parse_args()

    # Read script
    script_path = Path(args.script_file)
    if not script_path.exists():
        print(f"Error: script file not found: {args.script_file}", file=sys.stderr)
        sys.exit(1)
    script = script_path.read_text(encoding="utf-8")

    venue = args.venue or script_path.stem.replace("vapi-script-", "")

    print(f"📞 Initiating call to {args.to} ({args.language}) for {args.purpose}...")

    try:
        call_id = create_call(args.to, args.language, script, args.purpose)
        call = poll_call_result(call_id)
        result = parse_result(call, venue, args.purpose)
        save_output(result, args.output)
        print_summary(result)
        print(f"  Full result saved to: {args.output}")
    except VapiError as error:
        print(f"VapiError: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
