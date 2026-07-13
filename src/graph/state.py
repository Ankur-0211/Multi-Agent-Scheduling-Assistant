"""
Phase 2 — the real SchedulingState, replacing Phase 1's DummyState.
Matches the SDD's LangGraph State Schema (SDD section 6) exactly.
"""
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class BookingFields(TypedDict, total=False):
    name: Optional[str]
    email: Optional[str]
    date: Optional[str]
    time: Optional[str]
    purpose: Optional[str]


class SchedulingState(TypedDict):
    messages: Annotated[list, add_messages]   # full conversation, LangChain message objects
    intent: Optional[str]                      # "general" | "booking" | None
    booking_fields: BookingFields
    validation_error: Optional[str]
    available_slots: Optional[list]
    booking_confirmed: bool
    notification_status: Optional[str]