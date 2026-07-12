"""
Phase 1 proof-of-concept.

Run this script MULTIPLE TIMES (as separate `python poc_checkpoint.py`
invocations, i.e. separate processes) using the same thread_id.

Expected behavior:
- 1st run:  counter goes 0 -> 1 (node_a) -> 2 (node_b)
- 2nd run:  counter continues 2 -> 3 -> 4   (NOT reset to 0)
- 3rd run:  counter continues 4 -> 5 -> 6   ... and so on

This proves the SqliteSaver checkpoint is genuinely persisted to disk
(data/checkpoints.sqlite) and resumed correctly across fresh process
starts, keyed by thread_id -- which is the exact mechanism Assignment 2
relies on for both conversational memory and page-refresh recovery.
"""
import os

# Must be set before importing SqliteSaver (security: restricts
# checkpoint deserialization to known-safe types).
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from src.graph.builder import build_graph

DB_PATH = os.path.join("data", "checkpoints.sqlite")
THREAD_ID = "poc-thread-1"


def main():
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = build_graph(checkpointer)

    config = {"configurable": {"thread_id": THREAD_ID}}

    existing_state = graph.get_state(config)
    if existing_state.values:
        print(
            f"Resumed existing thread '{THREAD_ID}'. "
            f"Counter BEFORE this run: {existing_state.values.get('counter')}"
        )
        # Don't re-seed counter/log — pass an empty update so the
        # checkpointed values carry forward instead of being overwritten.
        run_input = {}
    else:
        print(f"No existing checkpoint for thread '{THREAD_ID}'. Starting fresh.")
        run_input = {"counter": 0, "log": []}

    result = graph.invoke(run_input, config)

    print("\n--- Result after this invocation ---")
    print(f"Counter: {result['counter']}")
    print("Log so far:")
    for entry in result["log"]:
        print(f"  - {entry}")

    conn.close()


if __name__ == "__main__":
    main()