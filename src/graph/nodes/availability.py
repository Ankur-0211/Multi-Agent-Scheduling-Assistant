"""
Availability Check + Offer Alternatives -- calls check_availability();
on conflict, formats up to 3 alternatives and ends the turn awaiting the
user's pick. Per SDD sections 5, 13.
"""
from datetime import datetime as dt

from langchain_core.messages import AIMessage

from src.graph.state import SchedulingState
from src.tools.check_availability import check_availability


def _pretty_slot(iso_datetime: str) -> str:
    d = dt.fromisoformat(iso_datetime)
    return d.strftime("%A %I:%M %p")


def availability_node(state: SchedulingState) -> dict:
    fields = dict(state["booking_fields"])
    result = check_availability(fields["date"], fields["time"])

    if result.get("error"):
        fields["date"] = None
        fields["time"] = None
        fields["date_raw"] = None
        fields["time_raw"] = None
        fields["datetime_confirmed"] = False
        return {
            "booking_fields": fields,
            "awaiting": "correction",
            "messages": [AIMessage(content=f"{result['error']} Could you give me a different date/time?")],
        }

    if result["available"]:
        return {"available_slots": None}

    alternatives = result.get("alternatives", [])
    if alternatives:
        pretty = ", ".join(_pretty_slot(a) for a in alternatives)
        msg = f"That slot's taken. Here are some nearby options: {pretty}. Which works for you?"
    else:
        msg = "That slot's taken and I couldn't find a nearby alternative right now -- could you suggest a different date/time?"

    fields["date"] = None
    fields["time"] = None
    fields["date_raw"] = None
    fields["time_raw"] = None
    fields["datetime_confirmed"] = False

    return {
        "booking_fields": fields,
        "awaiting": "alternatives",
        "available_slots": alternatives,
        "messages": [AIMessage(content=msg)],
    }


def route_after_availability(state: SchedulingState) -> str:
    if state.get("awaiting") in ("correction", "alternatives"):
        return "end_turn"
    return "reserve"