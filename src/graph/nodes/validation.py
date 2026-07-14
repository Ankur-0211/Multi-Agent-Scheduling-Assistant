"""
Validation Node -- normalizes date/time (Phase 3's dateparser wrapper),
validates email/business-hours/weekend/not-past (Phase 3's validators),
and explicitly confirms back to the user when a value was approximated.
Per SDD section 12.
"""
from datetime import datetime as dt

from langchain_core.messages import AIMessage

from src.graph.state import SchedulingState
from src.validation.datetime_parser import normalize_datetime
from src.validation.validators import validate_email, validate_not_weekend, validate_business_hours, validate_not_past


def _pretty(iso_date: str, iso_time: str) -> str:
    d = dt.fromisoformat(f"{iso_date}T{iso_time}")
    return d.strftime("%A, %B %d at %I:%M %p")


def _reset_datetime_fields(fields: dict) -> None:
    fields["date"] = None
    fields["time"] = None
    fields["date_raw"] = None
    fields["time_raw"] = None
    fields["datetime_confirmed"] = False
    fields["approximated"] = False


def validate_booking_node(state: SchedulingState) -> dict:
    fields = dict(state["booking_fields"])
    already_validated = fields.get("date") and fields.get("time") and fields.get("datetime_confirmed")

    if not already_validated:
        combined_text = f"{fields.get('date_raw', '')} {fields.get('time_raw', '')}".strip()
        result = normalize_datetime(combined_text)
        if not result["success"]:
            _reset_datetime_fields(fields)
            return {
                "booking_fields": fields,
                "awaiting": "correction",
                "messages": [AIMessage(content=f"{result['error']} Could you give me the date and time again?")],
            }
        fields["date"] = result["iso_date"]
        fields["time"] = result["iso_time"]
        fields["approximated"] = result["approximated"]
        fields["datetime_confirmed"] = False

    for check in (
        validate_email(fields["email"]),
        validate_not_weekend(fields["date"]),
        validate_business_hours(fields["time"]),
        validate_not_past(fields["date"], fields["time"]),
    ):
        if not check["valid"]:
            _reset_datetime_fields(fields)
            return {
                "booking_fields": fields,
                "awaiting": "correction",
                "messages": [AIMessage(content=f"{check['error']} Could you give me a different date/time?")],
            }

    if fields.get("approximated") and not fields.get("datetime_confirmed"):
        when = _pretty(fields["date"], fields["time"])
        return {
            "booking_fields": fields,
            "awaiting": "confirmation",
            "messages": [AIMessage(content=f"Just to confirm: {when} -- is that right?")],
        }

    fields["datetime_confirmed"] = True
    return {"booking_fields": fields, "awaiting": None}


def route_after_validate(state: SchedulingState) -> str:
    if state.get("awaiting") in ("correction", "confirmation"):
        return "end_turn"
    return "check_availability"