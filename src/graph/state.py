"""
Phase 5 -- extended SchedulingState. Adds `awaiting` (what the last
assistant message is waiting on) and the extra booking_fields keys needed
to track raw vs. normalized date/time and confirmation state across turns.
"""
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class BookingFields(TypedDict, total=False):
    name: Optional[str]
    email: Optional[str]
    date_raw: Optional[str]      # natural language, pre-validation
    time_raw: Optional[str]      # natural language, pre-validation
    date: Optional[str]          # ISO YYYY-MM-DD, once validated
    time: Optional[str]          # ISO HH:MM, once validated
    purpose: Optional[str]
    approximated: Optional[bool]        # was date/time guessed from a vague phrase?
    datetime_confirmed: Optional[bool]  # has the user confirmed an approximated value?
    booking_id: Optional[int]


class SchedulingState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: Optional[str]
    booking_fields: BookingFields
    validation_error: Optional[str]
    available_slots: Optional[list]
    booking_confirmed: bool
    notification_status: Optional[str]
    awaiting: Optional[str]  # "missing_fields" | "correction" | "confirmation" | "alternatives" | None