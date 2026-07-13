"""
Field-level validators -- email format, business hours, non-working days,
past-date checks. These run independently of any LLM judgment: per the
SDD's hidden-challenges note, validation must be enforced in code, since
prompt instructions alone aren't a reliability guarantee.
"""
import re
from datetime import date, datetime, time as dt_time
from typing import Optional

from src import config

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str) -> dict:
    if not email or not EMAIL_REGEX.match(email.strip()):
        return {"valid": False, "error": f"'{email}' doesn't look like a valid email address."}
    return {"valid": True, "error": None}


def validate_not_weekend(iso_date: str) -> dict:
    try:
        d = date.fromisoformat(iso_date)
    except ValueError:
        return {"valid": False, "error": f"'{iso_date}' is not a valid date."}
    if d.weekday() in config.NON_WORKING_WEEKDAYS:
        return {
            "valid": False,
            "error": f"{d.strftime('%A, %B %d')} is a non-working day. We're open Monday to Friday.",
        }
    return {"valid": True, "error": None}


def validate_business_hours(iso_time: str) -> dict:
    try:
        t = dt_time.fromisoformat(iso_time)
    except ValueError:
        return {"valid": False, "error": f"'{iso_time}' is not a valid time."}
    if not (config.BUSINESS_HOURS_START <= t.hour < config.BUSINESS_HOURS_END):
        return {
            "valid": False,
            "error": (
                f"{iso_time} is outside business hours "
                f"({config.BUSINESS_HOURS_START}:00\u2013{config.BUSINESS_HOURS_END}:00)."
            ),
        }
    return {"valid": True, "error": None}


def validate_not_past(iso_date: str, iso_time: str, reference_datetime: Optional[datetime] = None) -> dict:
    reference_datetime = reference_datetime or datetime.now()
    try:
        requested = datetime.fromisoformat(f"{iso_date}T{iso_time}")
    except ValueError:
        return {"valid": False, "error": f"'{iso_date} {iso_time}' is not a valid date/time."}
    if requested < reference_datetime:
        return {"valid": False, "error": "That date/time is in the past. Please choose a future slot."}
    return {"valid": True, "error": None}