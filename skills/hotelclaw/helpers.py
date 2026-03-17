"""hotelclaw helpers — shared utilities for tracking and formatting."""
import json
import os
from pathlib import Path

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
    """Save tracked properties to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRACKED_FILE, "w") as f:
        json.dump(data, f, indent=2)


def fmt_price(amount: float | None, currency: str = "USD") -> str:
    """Format a price for display."""
    if amount is None:
        return "n/a"
    return f"${amount:.0f} {currency}"
