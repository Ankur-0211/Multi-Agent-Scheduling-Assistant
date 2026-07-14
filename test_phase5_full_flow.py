"""
Phase 5 manual verification: two scenarios.
1) Straightforward multi-turn booking, WITH a simulated refresh mid-flow.
2) Unavailable slot -> alternatives -> pick one -> confirm.
"""
import os
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

import sqlite3
import uuid
from datetime import datetime, timedelta

from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage

from src import config
from src.persistence.appointments_db import init_db
from src.graph.builder import build_graph

config.validate_config()
init_db()


def open_graph():
    conn = sqlite3.connect(os.path.join("data", "checkpoints.sqlite"), check_same_thread=False)
    return build_graph(SqliteSaver(conn)), conn


def send(graph, cfg, text):
    print(f"\nUSER: {text}")
    result = graph.invoke({"messages": [HumanMessage(content=text)]}, cfg)
    ai_messages = [m for m in result["messages"] if getattr(m, "type", None) == "ai"]
    if ai_messages:
        print(f"ASSISTANT: {ai_messages[-1].content}")
    return result


def scenario_1_basic_booking_with_refresh():
    print("=" * 70)
    print("SCENARIO 1: basic booking, with a simulated refresh mid-flow")
    thread_id = f"phase5-basic-{uuid.uuid4()}"
    cfg = {"configurable": {"thread_id": thread_id}}

    graph, conn = open_graph()
    send(graph, cfg, "I'd like to book an appointment")
    send(graph, cfg, "My name is Ankur, email ankur@example.com")

    print("\n--- Simulating a page refresh (new connection, same thread_id) ---")
    conn.close()
    graph, conn = open_graph()

    send(graph, cfg, "Next Tuesday afternoon, for a general consultation")
    send(graph, cfg, "yes that works")  # confirms the "afternoon" approximation
    conn.close()


def scenario_2_unavailable_then_alternative():
    print("\n" + "=" * 70)
    print("SCENARIO 2: unavailable slot -> alternatives -> confirm")
    from src.tools.reserve_slot import reserve_slot
    from src.tools.check_availability import check_availability

    d = datetime.now().date() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    conflict_date = d.isoformat()

    reserve_slot(name="Existing Person", email="existing@example.com", date=conflict_date,
                 time="15:00", purpose="Pre-existing booking", thread_id="setup-thread")

    avail = check_availability(conflict_date, "15:00")
    alt_iso = avail["alternatives"][0]
    alt_date, alt_time = alt_iso.split("T")
    alt_text = f"{alt_date} at {alt_time}"  # unambiguous, dateparser-friendly

    thread_id = f"phase5-conflict-{uuid.uuid4()}"
    cfg = {"configurable": {"thread_id": thread_id}}
    graph, conn = open_graph()

    send(graph, cfg, "I want to book an appointment")
    send(graph, cfg, "My name is Priya, email priya@example.com, purpose is a checkup")
    send(graph, cfg, f"{conflict_date} at 15:00")  # should conflict -> alternatives offered
    send(graph, cfg, alt_text)  # explicit alternative -> should now succeed
    conn.close()


if __name__ == "__main__":
    scenario_1_basic_booking_with_refresh()
    scenario_2_unavailable_then_alternative()
    print("\nDone. Check data/appointments.sqlite for the new rows.")