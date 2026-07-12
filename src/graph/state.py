"""
Phase 1 — trivial state schema, just to prove checkpointing works.
The real SchedulingState (messages, intent, booking_fields, etc.)
is introduced in Phase 2 per the SDD.
"""
from typing import TypedDict, Annotated
import operator


class DummyState(TypedDict):
    counter: int
    # operator.add as the reducer means every node's returned "log" list
    # gets appended to the existing log, rather than overwriting it.
    log: Annotated[list[str], operator.add]