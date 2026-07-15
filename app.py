"""
Streamlit chat UI for the scheduling assistant. Per SDD section 17.

Key design point: the LangGraph checkpoint (keyed by thread_id) is the
ONLY source of truth for chat history -- there's no separate session_state
message list. Every rerun re-reads graph.get_state() and renders whatever's
there, which is what makes refresh-recovery work correctly (see section 14).
"""
import os
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

import uuid
import sqlite3

import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from src import config
from src.persistence.appointments_db import init_db
from src.graph.builder import build_graph

st.set_page_config(page_title="Multi-Agent Scheduling Assistant", page_icon="📅")


@st.cache_resource
def get_graph():
    conn = sqlite3.connect(os.path.join("data", "checkpoints.sqlite"), check_same_thread=False)
    return build_graph(SqliteSaver(conn))


try:
    config.validate_config()
except RuntimeError as e:
    st.error(str(e))
    st.stop()

init_db()
graph = get_graph()

# --- Thread ID via URL query param -- survives a hard refresh, unlike session_state ---
if "thread_id" not in st.query_params:
    st.query_params["thread_id"] = str(uuid.uuid4())
thread_id = st.query_params["thread_id"]
cfg = {"configurable": {"thread_id": thread_id}}

with st.sidebar:
    st.caption(f"Thread ID:\n`{thread_id}`")
    st.caption("Copy the URL above and reload it in a new tab to prove this conversation survives a refresh.")
    if st.button("🔄 Start a new conversation"):
        st.query_params.clear()
        st.rerun()

st.title("📅 Multi-Agent Scheduling Assistant")
st.caption("Ask me about our hours, or book an appointment right here in this chat.")

# --- Restore conversation from the checkpoint (source of truth for both LLM + UI) ---
snapshot = graph.get_state(cfg)
existing_messages = snapshot.values.get("messages", []) if snapshot.values else []

example_clicked = None
if not existing_messages:
    st.info("Try one of these to get started:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📆 Book me a slot next Tuesday afternoon"):
            example_clicked = "Book me a slot next Tuesday afternoon"
    with col2:
        if st.button("🕐 What are your hours?"):
            example_clicked = "What are your hours?"

for msg in existing_messages:
    role = "user" if getattr(msg, "type", None) == "human" else "assistant"
    with st.chat_message(role):
        st.write(msg.content)

# --- Confirmation card + notification indicator for the latest booking, if any ---
if snapshot.values and snapshot.values.get("booking_confirmed"):
    fields = snapshot.values.get("booking_fields", {})
    notif = snapshot.values.get("notification_status")
    with st.container(border=True):
        st.success(f"✅ Booking #{fields.get('booking_id')} confirmed for {fields.get('date')} at {fields.get('time')}.")
        if notif == "sent":
            st.caption("📨 Notification sent.")
        elif notif == "failed":
            st.caption("⚠️ Notification failed to send (booking is still confirmed).")

user_text = st.chat_input("Type your message...") or example_clicked

if user_text:
    with st.chat_message("user"):
        st.write(user_text)
    with st.chat_message("assistant"):
        reply = None
        with st.spinner("Thinking..."):
            try:
                result = graph.invoke({"messages": [HumanMessage(content=user_text)]}, cfg)
                ai_messages = [m for m in result["messages"] if getattr(m, "type", None) == "ai"]
                reply = ai_messages[-1].content if ai_messages else "..."
            except Exception as e:
                st.error(f"Something went wrong: {e}. Please try again -- your conversation so far is preserved.")
        if reply:
            st.write(reply)
    st.rerun()