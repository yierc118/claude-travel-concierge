import pytest
import sys
import os
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.calendar_sync import build_flight_event, build_hotel_event


def test_build_flight_event_returns_correct_structure():
    event = build_flight_event(
        flight_number="SQ321",
        origin="SIN",
        destination="NRT",
        departure_datetime="2026-05-14T09:45:00+08:00",
        arrival_datetime="2026-05-14T17:30:00+09:00",
        confirmation="ABC123"
    )
    assert event["summary"] == "✈️ SIN → NRT (SQ321)"
    assert event["start"]["dateTime"] == "2026-05-14T09:45:00+08:00"
    assert event["end"]["dateTime"] == "2026-05-14T17:30:00+09:00"
    assert "ABC123" in event["description"]


def test_build_hotel_event_returns_correct_structure():
    event = build_hotel_event(
        hotel_name="Shinjuku Granbell",
        city="Tokyo",
        check_in="2026-05-14",
        check_out="2026-05-18",
        confirmation="XYZ789"
    )
    assert event["summary"] == "🏨 Shinjuku Granbell (Tokyo)"
    assert event["start"]["date"] == "2026-05-14"
    assert event["end"]["date"] == "2026-05-18"
    assert "XYZ789" in event["description"]
