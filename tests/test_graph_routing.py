"""
Integration tests for the compiled LangGraph graph, with LLM calls mocked
via deterministic keyword-based fakes (same real Pydantic schemas, no API
calls/cost). Per SDD section 21. The appointments DB is isolated to a temp
file per test so this suite never touches real data.
"""
import os
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

import re
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import HumanMessage

from src.graph.nodes.triage import IntentClassification
from src.graph.nodes.collect_info import BookingExtraction
from src.graph.builder import build_graph

BOOKING_KEYWORDS = ["book", "schedule", "appointment", "reserve"]


class _FakeStructuredLLM:
    def __init__(self, schema):
        self._schema = schema

    def invoke(self, messages):
        user_text = messages[-1].content.lower()
        if self._schema is IntentClassification:
            if any(k in user_text for k in BOOKING_KEYWORDS):
                return IntentClassification(intent="booking", general_answer=None)
            return IntentClassification(intent="general", general_answer="We're open Monday to Friday, 9 AM to 6 PM.")
        if self._schema is BookingExtraction:
            return _fake_extract(messages[-1].content)
        raise AssertionError(f"Unexpected schema requested: {self._schema}")


class _FakeChatModel:
    def __init__(self, *args, **kwargs):
        pass

    def with_structured_output(self, schema):
        return _FakeStructuredLLM(schema)


def _fake_extract(text: str) -> BookingExtraction:
    """Deterministic stand-in for real LLM extraction -- good enough to
    exercise graph routing without needing real NLU."""
    name = email = date_text = time_text = purpose = None

    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    if email_match:
        email = email_match.group(0)

    name_match = re.search(r"name is (\w+)", text, re.IGNORECASE)
    if name_match:
        name = name_match.group(1)

    iso_date_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if iso_date_match:
        date_text = iso_date_match.group(0)
    else:
        for wd in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            if wd in text.lower():
                prefix = "next " if "next" in text.lower() else ""
                date_text = f"{prefix}{wd.capitalize()}"
                break
        if re.search(r"\btomorrow\b", text, re.IGNORECASE):
            date_text = "tomorrow"

    time_match = re.search(r"\b(\d{1,2}\s?(am|pm)|\d{1,2}:\d{2})\b", text, re.IGNORECASE)
    if time_match:
        time_text = time_match.group(0)

    purpose_match = re.search(r"purpose is ([\w\s]+)", text, re.IGNORECASE)
    if purpose_match:
        purpose = purpose_match.group(1).strip()
    elif "consultation" in text.lower():
        purpose = "consultation"
    elif "checkup" in text.lower():
        purpose = "checkup"

    return BookingExtraction(name=name, email=email, date_text=date_text, time_text=time_text, purpose=purpose)


@pytest.fixture(autouse=True)
def isolated_appointments_db(tmp_path, monkeypatch):
    """Redirects the appointments DB to a temp file for every test in this
    file, so the integration suite never touches real app data."""
    from src.persistence import appointments_db
    test_db_path = str(tmp_path / "test_appointments.sqlite")
    monkeypatch.setattr(appointments_db, "DB_PATH", test_db_path)
    appointments_db.init_db()
    yield


@pytest.fixture
def graph_with_mocked_llm():
    with patch("src.graph.nodes.triage.ChatGoogleGenerativeAI", _FakeChatModel), \
         patch("src.graph.nodes.collect_info.ChatGoogleGenerativeAI", _FakeChatModel):
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        graph = build_graph(SqliteSaver(conn))
        yield graph
        conn.close()


def _invoke(graph, thread_id, text):
    cfg = {"configurable": {"thread_id": thread_id, "model": "fake-model"}}
    result = graph.invoke({"messages": [HumanMessage(content=text)]}, cfg)
    ai_messages = [m for m in result["messages"] if getattr(m, "type", None) == "ai"]
    reply = ai_messages[-1].content if ai_messages else None
    return result, reply


def test_general_query_path():
    with patch("src.graph.nodes.triage.ChatGoogleGenerativeAI", _FakeChatModel):
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        graph = build_graph(SqliteSaver(conn))
        result, reply = _invoke(graph, f"test-{uuid.uuid4()}", "What are your business hours?")
        assert result["intent"] == "general"
        assert reply is not None
        conn.close()


def test_booking_intent_routes_to_collect_info(graph_with_mocked_llm):
    thread_id = f"test-{uuid.uuid4()}"
    result, reply = _invoke(graph_with_mocked_llm, thread_id, "I'd like to book an appointment")
    assert result["intent"] == "booking"
    assert result["awaiting"] == "missing_fields"


def test_full_booking_flow_end_to_end(graph_with_mocked_llm):
    thread_id = f"test-{uuid.uuid4()}"
    graph = graph_with_mocked_llm

    _invoke(graph, thread_id, "I'd like to book an appointment")
    _invoke(graph, thread_id, "My name is Ankur, email ankur@example.com")
    result, reply = _invoke(graph, thread_id, "Next Friday at 3pm for a consultation")

    assert result["booking_confirmed"] is True
    assert result["booking_fields"]["booking_id"] is not None
    assert "confirmed" in reply.lower()


def test_refresh_recovery_mid_booking():
    """A NEW graph instance (fresh connection object, same on-disk checkpoint
    file and thread_id) resumes correctly mid-flow -- the automated version
    of the manual refresh test."""
    with patch("src.graph.nodes.triage.ChatGoogleGenerativeAI", _FakeChatModel), \
         patch("src.graph.nodes.collect_info.ChatGoogleGenerativeAI", _FakeChatModel):

        db_path = tempfile.mktemp(suffix=".sqlite")
        thread_id = f"test-{uuid.uuid4()}"

        conn1 = sqlite3.connect(db_path, check_same_thread=False)
        graph1 = build_graph(SqliteSaver(conn1))
        _invoke(graph1, thread_id, "I'd like to book an appointment")
        _invoke(graph1, thread_id, "My name is Priya, email priya@example.com")
        conn1.close()

        conn2 = sqlite3.connect(db_path, check_same_thread=False)
        graph2 = build_graph(SqliteSaver(conn2))
        cfg = {"configurable": {"thread_id": thread_id, "model": "fake-model"}}
        snapshot = graph2.get_state(cfg)

        assert snapshot.values["booking_fields"]["name"] == "Priya"
        assert snapshot.values["booking_fields"]["email"] == "priya@example.com"
        conn2.close()


def test_unavailable_slot_then_alternative(graph_with_mocked_llm):
    from src.tools.reserve_slot import reserve_slot
    from src.tools.check_availability import check_availability

    d = datetime.now().date() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    conflict_date = d.isoformat()

    reserve_slot(name="Existing", email="existing@example.com", date=conflict_date,
                 time="15:00", purpose="pre-existing", thread_id="setup")

    avail = check_availability(conflict_date, "15:00")
    alt_date, alt_time = avail["alternatives"][0].split("T")

    graph = graph_with_mocked_llm
    thread_id = f"test-{uuid.uuid4()}"

    _invoke(graph, thread_id, "I want to book an appointment")
    _invoke(graph, thread_id, "My name is Priya, email priya@example.com, purpose is checkup")
    result1, _ = _invoke(graph, thread_id, f"{conflict_date} at 15:00")
    assert result1["awaiting"] == "alternatives"

    result2, _ = _invoke(graph, thread_id, f"{alt_date} at {alt_time}")
    assert result2["booking_confirmed"] is True