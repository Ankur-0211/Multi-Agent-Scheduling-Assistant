"""
Reservation Node -- calls reserve_slot(), which re-checks availability
atomically. On a race-condition conflict, resets date/time so the user
can pick again. Per SDD sections 5, 10.
"""
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from src.graph.state import SchedulingState
from src.tools.reserve_slot import reserve_slot


def reservation_node(state: SchedulingState, config: RunnableConfig) -> dict:
    fields = dict(state["booking_fields"])
    thread_id = config["configurable"]["thread_id"]

    result = reserve_slot(
        name=fields["name"], email=fields["email"], date=fields["date"],
        time=fields["time"], purpose=fields["purpose"], thread_id=thread_id,
    )

    if not result["success"]:
        fields["date"] = None
        fields["time"] = None
        fields["date_raw"] = None
        fields["time_raw"] = None
        fields["datetime_confirmed"] = False
        return {
            "booking_fields": fields,
            "awaiting": "correction",
            "messages": [AIMessage(content=result["error"])],
        }

    fields["booking_id"] = result["booking_id"]
    return {"booking_fields": fields}


def route_after_reservation(state: SchedulingState) -> str:
    if state.get("awaiting") == "correction":
        return "end_turn"
    return "notify"