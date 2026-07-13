"""
Unit tests for field-level validators: email, business hours, weekends,
past-date checks.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
from src.validation.validators import (
    validate_email,
    validate_not_weekend,
    validate_business_hours,
    validate_not_past,
)

MOCK_NOW = datetime(2026, 7, 13, 10, 0, 0)  # Monday, July 13, 2026, 10 AM


def test_valid_email():
    assert validate_email("ankur@example.com")["valid"] is True


def test_invalid_email_missing_at():
    result = validate_email("ankurexample.com")
    assert result["valid"] is False
    assert "error" in result


def test_invalid_email_missing_domain():
    assert validate_email("ankur@example")["valid"] is False


def test_weekday_is_valid():
    # July 14, 2026 is a Tuesday
    assert validate_not_weekend("2026-07-14")["valid"] is True


def test_saturday_is_rejected():
    # July 18, 2026 is a Saturday
    result = validate_not_weekend("2026-07-18")
    assert result["valid"] is False
    assert "non-working day" in result["error"]


def test_sunday_is_rejected():
    # July 19, 2026 is a Sunday
    assert validate_not_weekend("2026-07-19")["valid"] is False


def test_business_hours_valid():
    assert validate_business_hours("15:00")["valid"] is True


def test_business_hours_too_early():
    result = validate_business_hours("08:00")
    assert result["valid"] is False


def test_business_hours_too_late():
    result = validate_business_hours("18:00")  # end boundary, exclusive
    assert result["valid"] is False


def test_business_hours_start_boundary_inclusive():
    assert validate_business_hours("09:00")["valid"] is True


def test_future_datetime_is_valid():
    result = validate_not_past("2026-07-14", "15:00", reference_datetime=MOCK_NOW)
    assert result["valid"] is True


def test_past_datetime_is_rejected():
    result = validate_not_past("2026-07-01", "10:00", reference_datetime=MOCK_NOW)
    assert result["valid"] is False
    assert "past" in result["error"]