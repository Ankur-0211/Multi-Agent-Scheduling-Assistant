"""
Phase 2 manual verification script.

Runs a fixed set of example messages (each on its own fresh thread,
to isolate routing behavior) and prints the detected intent + response,
so we can manually confirm the Triage Agent classifies correctly.
"""
import os
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

import sqlite3
import uuid

from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage

from src import config
from src.graph.builder import build_graph

config.validate_config()

TEST_MESSAGES = [
    "What are your business hours?",
    "I'd like to book an appointment for next Tuesday at 3pm.",
    "Can you schedule a meeting with me?",
    "Do you offer consultations?",
    "I want to see the doctor next Friday morning.",
    "hey, anyone there?",  # ambiguous small talk -> should stay general
]


def main():
    conn = sqlite3.connect(os.path.join("data", "checkpoints.sqlite"), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = build_graph(checkpointer)

    for msg in TEST_MESSAGES:
        thread_id = f"phase2-test-{uuid.uuid4()}"
        cfg = {"configurable": {"thread_id": thread_id}}
        print(f"\n>>> Sending: {msg!r}  (this may take a few seconds)")
        result = graph.invoke({"messages": [HumanMessage(content=msg)]}, cfg)

        print("=" * 60)
        print(f"User: {msg}")
        print(f"Detected intent: {result.get('intent')}")
        ai_messages = [m for m in result["messages"] if getattr(m, "type", None) == "ai"]
        if ai_messages:
            print(f"Assistant: {ai_messages[-1].content}")

    conn.close()


if __name__ == "__main__":
    main()