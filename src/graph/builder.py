"""
Phase 5 -- full Booking Specialist subgraph, replacing the Phase 2 stub.
Per SDD section 5 (LangGraph Workflow) and section 11 (stay in the
booking subgraph across turns without re-routing through Triage).
"""
from langgraph.graph import StateGraph, START, END

from src.graph.state import SchedulingState
from src.graph.nodes.triage import triage_node, route_from_triage
from src.graph.nodes.collect_info import collect_info_node, route_after_collect_info
from src.graph.nodes.validation import validate_booking_node, route_after_validate
from src.graph.nodes.availability import availability_node, route_after_availability
from src.graph.nodes.reservation import reservation_node, route_after_reservation
from src.graph.nodes.notification import notification_node
from src.graph.nodes.confirmation import confirmation_node


def route_from_start(state: SchedulingState) -> str:
    if state.get("intent") == "booking" and not state.get("booking_confirmed"):
        return "collect_info"
    return "triage"


def build_graph(checkpointer):
    graph = StateGraph(SchedulingState)

    graph.add_node("triage", triage_node)
    graph.add_node("collect_info", collect_info_node)
    graph.add_node("validate_booking", validate_booking_node)
    graph.add_node("check_availability", availability_node)
    graph.add_node("reserve", reservation_node)
    graph.add_node("notify", notification_node)
    graph.add_node("confirm", confirmation_node)

    graph.add_conditional_edges(START, route_from_start, {"triage": "triage", "collect_info": "collect_info"})
    graph.add_conditional_edges("triage", route_from_triage, {"booking": "collect_info", "general_end": END})
    graph.add_conditional_edges("collect_info", route_after_collect_info, {"end_turn": END, "validate": "validate_booking"})
    graph.add_conditional_edges("validate_booking", route_after_validate, {"end_turn": END, "check_availability": "check_availability"})
    graph.add_conditional_edges("check_availability", route_after_availability, {"end_turn": END, "reserve": "reserve"})
    graph.add_conditional_edges("reserve", route_after_reservation, {"end_turn": END, "notify": "notify"})
    graph.add_edge("notify", "confirm")
    graph.add_edge("confirm", END)

    return graph.compile(checkpointer=checkpointer)