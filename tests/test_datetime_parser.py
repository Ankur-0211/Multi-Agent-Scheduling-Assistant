"""
Unit tests for date/time normalization.
Uses a FIXED mock 'today' (Monday, July 13, 2026) so results are
deterministic regardless of when the suite actually runs -- per the
SDD's explicit call-out that 'next Friday' resolves differently
depending on the day it's said.

All expected values below were verified against real dateparser output
before being written here (not assumed).
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
from src.validation.datetime_parser import normalize_date, normalize_time, normalize_datetime

MOCK_TODAY = datetime(2026, 7, 13, 10, 0, 0)  # a Monday


def test_next_friday():
    result = normalize_date("next Friday", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_date"] == "2026-07-17"


def test_this_friday_same_as_next_friday():
    result = normalize_date("this Friday", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_date"] == "2026-07-17"


def test_tomorrow():
    result = normalize_date("tomorrow", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_date"] == "2026-07-14"


def test_in_three_days():
    result = normalize_date("in 3 days", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_date"] == "2026-07-16"


def test_explicit_iso_date_passthrough():
    result = normalize_date("2026-08-01", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_date"] == "2026-08-01"


def test_unparseable_date_returns_error():
    result = normalize_date("blorptuesday", reference_date=MOCK_TODAY)
    assert result["success"] is False
    assert "error" in result


def test_time_3pm():
    result = normalize_time("3pm", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_time"] == "15:00"


def test_time_24_hour_format():
    result = normalize_time("15:00", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_time"] == "15:00"


def test_combined_next_tuesday_at_3pm():
    result = normalize_datetime("next Tuesday at 3pm", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_date"] == "2026-07-14"
    assert result["iso_time"] == "15:00"
    assert result["approximated"] is False


def test_daypart_approximation_next_tuesday_afternoon():
    result = normalize_datetime("next Tuesday afternoon", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_date"] == "2026-07-14"
    assert result["iso_time"] == "14:00"
    assert result["approximated"] is True


def test_daypart_approximation_friday_morning():
    result = normalize_datetime("Friday morning", reference_date=MOCK_TODAY)
    assert result["success"] is True
    assert result["iso_date"] == "2026-07-17"
    assert result["iso_time"] == "09:00"
    assert result["approximated"] is True