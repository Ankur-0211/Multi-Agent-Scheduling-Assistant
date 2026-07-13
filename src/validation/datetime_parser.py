"""
Wraps `dateparser` to normalize natural-language dates/times to ISO,
always relative to an explicit reference date (never dateparser's own
silent default of "now"), so results are deterministic and testable.

IMPORTANT DISCOVERY (verified by direct testing, not assumed):
dateparser cannot parse "next Friday" / "this Friday" / "next Tuesday at 3pm"
style phrases AT ALL -- it returns None regardless of settings. Bare weekday
names ("Friday") parse correctly as the nearest upcoming occurrence, so we
strip "next "/"this " before weekday names as a preprocessing step.

Similarly, vague day-parts ("Friday morning") fail outright, so we map them
to a representative time and flag the result as `approximated` -- the
Booking Specialist (Phase 5) is expected to explicitly confirm any
approximated value back to the user, per SDD section 12.
"""
import re
from datetime import datetime
from typing import Optional

import dateparser

_NEXT_THIS_WEEKDAY_RE = re.compile(
    r"\b(?:next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)

_DAYPART_RE = re.compile(r"\b(morning|afternoon|evening|night)\b", re.IGNORECASE)
_DAYPART_DEFAULTS = {
    "morning": "9am",
    "afternoon": "2pm",
    "evening": "5pm",
    "night": "7pm",
}


def _preprocess(text: str) -> tuple[str, bool]:
    approximated = False
    text = _NEXT_THIS_WEEKDAY_RE.sub(lambda m: m.group(1), text)

    if _DAYPART_RE.search(text) and not re.search(r"\d", text):
        approximated = True
        text = _DAYPART_RE.sub(lambda m: _DAYPART_DEFAULTS[m.group(1).lower()], text)

    return text, approximated


def _parse(text: str, reference_date: Optional[datetime]):
    reference_date = reference_date or datetime.now()
    processed_text, approximated = _preprocess(text)
    settings = {"RELATIVE_BASE": reference_date, "PREFER_DATES_FROM": "future"}
    parsed = dateparser.parse(processed_text, settings=settings)
    return parsed, approximated


def normalize_date(text: str, reference_date: Optional[datetime] = None) -> dict:
    """Parse a natural-language date phrase into ISO format (YYYY-MM-DD)."""
    parsed, approximated = _parse(text, reference_date)
    if parsed is None:
        return {
            "success": False,
            "error": f"Couldn't understand the date '{text}'. Try something like 'next Tuesday' or '2026-07-21'.",
        }
    return {"success": True, "iso_date": parsed.date().isoformat(), "approximated": approximated}


def normalize_time(text: str, reference_date: Optional[datetime] = None) -> dict:
    """Parse a natural-language time phrase into 24-hour ISO format (HH:MM)."""
    parsed, approximated = _parse(text, reference_date)
    if parsed is None:
        return {
            "success": False,
            "error": f"Couldn't understand the time '{text}'. Try something like '3pm' or '15:00'.",
        }
    return {"success": True, "iso_time": parsed.strftime("%H:%M"), "approximated": approximated}


def normalize_datetime(text: str, reference_date: Optional[datetime] = None) -> dict:
    """Parse a combined date+time phrase (e.g. 'next Tuesday at 3pm') in one pass."""
    parsed, approximated = _parse(text, reference_date)
    if parsed is None:
        return {
            "success": False,
            "error": f"Couldn't understand '{text}'. Try something like 'next Tuesday at 3pm'.",
        }
    return {
        "success": True,
        "iso_date": parsed.date().isoformat(),
        "iso_time": parsed.strftime("%H:%M"),
        "approximated": approximated,
    }