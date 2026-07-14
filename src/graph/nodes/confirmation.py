"""
Confirmation Node -- finalizes the turn: marks booking_confirmed True and
composes the final message. Functions as the SDD's "Memory Update Node"
(actual persistence is automatic via SqliteSaver).
"""
from datetime import datetime as dt

from langchain_core.messages import AIMessage

from src.graph.state import SchedulingState


def _pretty(iso_date: str, iso_time: str) -> str:
    d = dt.fromisoformat(f"{iso_date}T{iso_time}")
    return d.strftime("%A, %B %d at %I:%M %p")


def confirmation_node(state: SchedulingState) -> dict:
    fields = state["booking_fields"]
    when = _pretty(fields["date"], fields["time"])
    notif_note = (
        "A confirmation notification was sent."
        if state.get("notification_status") == "sent"
        else "Note: the confirmation notification failed to send, but your booking is confirmed."
    )
    msg = (
        f"You're all set, {fields['name']}! Booking #{fields['booking_id']} confirmed for "
        f"{when} -- {fields['purpose']}. {notif_note}"
    )
    return {"booking_confirmed": True, "messages": [AIMessage(content=msg)]}