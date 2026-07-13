"""
Phase 2 — real routing graph: triage -> (general answer -> END)
                                      -> (booking stub -> END)

The Booking Specialist stub is a placeholder; the real subgraph
(collect info, validate, check availability, reserve, notify) is
built in Phase 5 per the SDD's phase plan.
"""
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END

from src.graph.state import SchedulingState
from src.graph.nodes.triage import triage_node, route_from_triage


def booking_specialist_stub(state: SchedulingState) -> dict:
    return {
        "messages": [
            AIMessage(
                content="[STUB] The Booking Specialist would take over here. "
                "(Real booking flow is built in Phase 5.)"
            )
        ]
    }


def build_graph(checkpointer):
    graph = StateGraph(SchedulingState)

    graph.add_node("triage", triage_node)
    graph.add_node("booking_specialist_stub", booking_specialist_stub)

    graph.add_edge(START, "triage")
    graph.add_conditional_edges(
        "triage",
        route_from_triage,
        {
            "booking": "booking_specialist_stub",
            "general_end": END,
        },
    )
    graph.add_edge("booking_specialist_stub", END)

    return graph.compile(checkpointer=checkpointer)