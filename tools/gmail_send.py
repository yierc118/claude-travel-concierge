"""
Gmail send tool — sends emails from caoyier118@gmail.com via the Gmail API.
Used by the budget tracking cron and booking agent for confirmation drafts.

First-time setup (run once to authenticate):
    python3 tools/gmail_send.py --auth

Then send an email:
    python3 tools/gmail_send.py \
        --to "caoyier118@gmail.com" \
        --subject "✈️ Travel Price Report — 2026-03-17" \
        --body "Report content here" \
        --body-file "output/report.html"   # alternative: read body from file

Credentials:
    GMAIL_CREDENTIALS_PATH  — path to OAuth client credentials JSON
                              (downloaded from Google Cloud Console)
                              default: ~/.config/travel-concierge/gmail-credentials.json
    GMAIL_TOKEN_PATH        — path to store the OAuth token after first auth
                              default: ~/.config/travel-concierge/gmail-token.json

Setup steps:
    1. Google Cloud Console → New project → Enable Gmail API
    2. Credentials → Create → OAuth 2.0 Client ID → Desktop app → Download JSON
    3. Save JSON to ~/.config/travel-concierge/gmail-credentials.json
    4. Run: python3 tools/gmail_send.py --auth
    5. Browser opens → log in as caoyier118@gmail.com → grant access
    6. Token saved. Future calls use the token automatically (auto-refreshes).
"""

import argparse
import base64
import json
import os
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

DEFAULT_CREDENTIALS_PATH = Path.home() / ".config" / "travel-concierge" / "gmail-credentials.json"
DEFAULT_TOKEN_PATH = Path.home() / ".config" / "travel-concierge" / "gmail-token.json"

SENDER = os.environ.get("GMAIL_SENDER", "clawdia.12.ai@gmail.com")


class GmailError(Exception):
    pass


def _credentials_path() -> Path:
    env = os.environ.get("GMAIL_CREDENTIALS_PATH")
    return Path(env) if env else DEFAULT_CREDENTIALS_PATH


def _token_path() -> Path:
    env = os.environ.get("GMAIL_TOKEN_PATH")
    return Path(env) if env else DEFAULT_TOKEN_PATH


def _get_credentials() -> Credentials:
    """Load credentials from token file, refreshing if expired. Raises if not authenticated."""
    token_path = _token_path()

    if not token_path.exists():
        raise GmailError(
            f"Not authenticated. Run: python3 tools/gmail_send.py --auth\n"
            f"(token not found at {token_path})"
        )

    credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        _save_token(credentials)

    if not credentials.valid:
        raise GmailError(
            "Gmail credentials are invalid or expired. "
            "Re-run: python3 tools/gmail_send.py --auth"
        )

    return credentials


def _save_token(credentials: Credentials) -> None:
    token_path = _token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json())


def run_auth_flow() -> None:
    """Run the OAuth browser flow. Call once to authenticate."""
    credentials_path = _credentials_path()

    if not credentials_path.exists():
        print(
            f"Error: credentials file not found at {credentials_path}\n"
            "\nSetup:\n"
            "  1. Google Cloud Console → Enable Gmail API\n"
            "  2. Credentials → OAuth 2.0 Client ID → Desktop app → Download JSON\n"
            f"  3. Save as: {credentials_path}"
        )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    credentials = flow.run_local_server(port=0)
    _save_token(credentials)
    print(f"✅ Authentication successful. Token saved to: {_token_path()}")


def build_message(to: str, subject: str, body: str, html: bool = False) -> dict:
    """Build a Gmail API message dict from components."""
    if html:
        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["From"] = SENDER
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
    else:
        msg = MIMEText(body, "plain")
        msg["To"] = to
        msg["From"] = SENDER
        msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def send_email(to: str, subject: str, body: str, html: bool = False) -> str:
    """
    Send an email. Returns the sent message ID.

    Args:
        to:      recipient email address
        subject: email subject line
        body:    email body (plain text or HTML)
        html:    set True if body is HTML

    Returns:
        Gmail message ID of the sent message
    """
    credentials = _get_credentials()

    try:
        service = build("gmail", "v1", credentials=credentials)
        message = build_message(to, subject, body, html=html)
        result = service.users().messages().send(userId="me", body=message).execute()
        return result["id"]
    except HttpError as error:
        raise GmailError(f"Gmail API error: {error}") from error


def create_draft(to: str, subject: str, body: str, html: bool = False) -> str:
    """
    Save a draft without sending. Returns the draft ID.
    """
    credentials = _get_credentials()

    try:
        service = build("gmail", "v1", credentials=credentials)
        message = build_message(to, subject, body, html=html)
        draft = service.users().drafts().create(
            userId="me", body={"message": message}
        ).execute()
        return draft["id"]
    except HttpError as error:
        raise GmailError(f"Gmail API error: {error}") from error


def main() -> None:
    parser = argparse.ArgumentParser(description="Send email via Gmail API.")
    parser.add_argument("--auth", action="store_true", help="Run OAuth flow (first-time setup)")
    parser.add_argument("--to", help="Recipient email address")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--body", help="Email body text")
    parser.add_argument("--body-file", help="Path to file containing email body")
    parser.add_argument("--html", action="store_true", help="Treat body as HTML")
    parser.add_argument("--draft", action="store_true", help="Save as draft instead of sending")
    args = parser.parse_args()

    if args.auth:
        run_auth_flow()
        return

    # Validate required args for send/draft
    if not args.to:
        print("Error: --to is required", file=sys.stderr)
        sys.exit(1)
    if not args.subject:
        print("Error: --subject is required", file=sys.stderr)
        sys.exit(1)

    # Get body from --body or --body-file
    if args.body_file:
        body_path = Path(args.body_file)
        if not body_path.exists():
            print(f"Error: body file not found: {args.body_file}", file=sys.stderr)
            sys.exit(1)
        body = body_path.read_text(encoding="utf-8")
    elif args.body:
        body = args.body
    else:
        print("Error: --body or --body-file is required", file=sys.stderr)
        sys.exit(1)

    try:
        if args.draft:
            draft_id = create_draft(args.to, args.subject, body, html=args.html)
            print(f"✅ Draft saved (ID: {draft_id})")
        else:
            message_id = send_email(args.to, args.subject, body, html=args.html)
            print(f"✅ Email sent (ID: {message_id})")
    except GmailError as error:
        print(f"GmailError: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
