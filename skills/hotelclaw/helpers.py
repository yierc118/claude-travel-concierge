"""hotelclaw helpers — shared utilities for tracking and formatting."""
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
TRACKED_FILE = DATA_DIR / "tracked.json"


def get_data_path() -> Path:
    return TRACKED_FILE


def load_tracked() -> list:
    """Load tracked properties from JSON. Returns empty list if file missing."""
    if not TRACKED_FILE.exists():
        return []
    try:
        with open(TRACKED_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_tracked(data: list) -> None:
    """Save tracked properties to JSON using atomic write to prevent data corruption."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, TRACKED_FILE)
    except Exception:
        os.unlink(tmp_path)
        raise


def fmt_price(amount: Optional[float], currency: str = "USD") -> str:
    """Format a price for display."""
    if amount is None:
        return "n/a"
    return f"${amount:.0f} {currency}"
