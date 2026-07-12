"""
Phase 1 — a trivial two-node graph: node_a -> node_b -> END.
Each node increments a counter and appends a log entry.
This is only meant to prove SqliteSaver checkpointing works end-to-end
before any real agent/tool logic is built on top of it.
"""
from langgraph.graph import StateGraph, START, END

from src.graph.state import DummyState


def node_a(state: DummyState) -> dict:
    new_count = state.get("counter", 0) + 1
    print(f"[node_a] counter is now {new_count}")
    return {"counter": new_count, "log": [f"node_a ran, counter={new_count}"]}


def node_b(state: DummyState) -> dict:
    new_count = state.get("counter", 0) + 1
    print(f"[node_b] counter is now {new_count}")
    return {"counter": new_count, "log": [f"node_b ran, counter={new_count}"]}


def build_graph(checkpointer):
    graph = StateGraph(DummyState)
    graph.add_node("node_a", node_a)
    graph.add_node("node_b", node_b)
    graph.add_edge(START, "node_a")
    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", END)
    return graph.compile(checkpointer=checkpointer)