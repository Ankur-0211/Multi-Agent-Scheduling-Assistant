"""
Collect Missing Info Node -- extracts whatever booking fields it can from
the user's latest message via structured LLM output, merges them into
booking_fields, and asks for exactly what's still missing (never re-asking
for known fields). Also handles the confirmation fast-path and topic
abandonment detection. Per SDD sections 5, 12, 13.
"""
import re
from typing import Optional

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src import config
from src.graph.state import SchedulingState

REQUIRED_FIELDS = ["name", "email", "date_raw", "time_raw", "purpose"]
FIELD_PROMPTS = {
    "name": "your name",
    "email": "your email address",
    "date_raw": "what date you'd like",
    "time_raw": "what time you'd like",
    "purpose": "the purpose of the appointment",
}

_AFFIRMATIVE_RE = re.compile(
    r"\b(yes|yeah|yep|yup|correct|right|confirm(ed)?|sounds good|that works|ok(ay)?|sure|perfect)\b",
    re.IGNORECASE,
)


class BookingExtraction(BaseModel):
    name: Optional[str] = Field(default=None, description="The user's full name, if mentioned in THIS message.")
    email: Optional[str] = Field(default=None, description="The user's email address, if mentioned in THIS message.")
    date_text: Optional[str] = Field(default=None, description="Raw natural-language date phrase, verbatim, if mentioned in THIS message.")
    time_text: Optional[str] = Field(default=None, description="Raw natural-language time phrase, verbatim, if mentioned in THIS message.")
    purpose: Optional[str] = Field(default=None, description="The reason/purpose for the appointment, if mentioned in THIS message.")


EXTRACTION_SYSTEM_PROMPT = """You extract booking details from a user's message for a scheduling
assistant. Only extract fields the user actually mentioned in THIS message --
leave a field null if it wasn't mentioned. Do not guess or invent values."""


def _last_human_message(messages) -> str:
    for m in reversed(messages):
        if getattr(m, "type", None) == "human":
            return m.content
    return ""


def _extract_fields(user_text: str) -> BookingExtraction:
    llm = ChatGoogleGenerativeAI(model=config.GEMINI_MODEL, google_api_key=config.GEMINI_API_KEY, thinking_level="low")
    structured_llm = llm.with_structured_output(BookingExtraction)
    try:
        return structured_llm.invoke([SystemMessage(content=EXTRACTION_SYSTEM_PROMPT), HumanMessage(content=user_text)])
    except Exception as e:
        print(f"[collect_info] extraction failed ({e}); assuming nothing new was provided.")
        return BookingExtraction()


def _missing_fields(fields: dict) -> list:
    return [f for f in REQUIRED_FIELDS if not fields.get(f)]


def _ask_for_missing(missing: list) -> str:
    asked = missing[:2]  # ask for at most 2 at a time, per SDD
    phrased = " and ".join(FIELD_PROMPTS[f] for f in asked)
    return f"Could you tell me {phrased}?"


def collect_info_node(state: SchedulingState) -> dict:
    user_text = _last_human_message(state["messages"])
    fields = dict(state.get("booking_fields") or {})
    awaiting = state.get("awaiting")

    # Fast-path: waiting on a yes/no confirmation of an approximated time.
    if awaiting == "confirmation" and not fields.get("datetime_confirmed", False):
        if _AFFIRMATIVE_RE.search(user_text):
            fields["datetime_confirmed"] = True
            return {"booking_fields": fields, "awaiting": None}
        # Not a clear "yes" -- fall through, treat as a correction attempt below.

    extraction = _extract_fields(user_text)
    got_anything = any([extraction.name, extraction.email, extraction.date_text, extraction.time_text, extraction.purpose])

    if not got_anything:
        # Only check for topic-abandonment if we'd already asked for something
        # specific (awaiting is not None). On the very first hand-off turn
        # (awaiting is None), Triage just classified this exact message as
        # "booking" a moment ago -- re-checking it again would be a wasted call.
        if awaiting is not None:
            from src.graph.nodes.triage import triage_node as _classify
            triage_result = _classify(state)
            if triage_result.get("intent") == "general":
                return {
                    "intent": "general",
                    "awaiting": None,
                    "messages": triage_result.get("messages", []),
                }
        missing = _missing_fields(fields)
        return {
            "booking_fields": fields,
            "awaiting": "missing_fields",
            "messages": [AIMessage(content=_ask_for_missing(missing) if missing else "Could you clarify that?")],
        }

    if extraction.name:
        fields["name"] = extraction.name
    if extraction.email:
        fields["email"] = extraction.email
    if extraction.date_text:
        fields["date_raw"] = extraction.date_text
        fields["date"] = None
        fields["approximated"] = False
        fields["datetime_confirmed"] = False
    if extraction.time_text:
        fields["time_raw"] = extraction.time_text
        fields["time"] = None
        fields["approximated"] = False
        fields["datetime_confirmed"] = False
    if extraction.purpose:
        fields["purpose"] = extraction.purpose

    missing = _missing_fields(fields)
    if missing:
        return {
            "booking_fields": fields,
            "awaiting": "missing_fields",
            "messages": [AIMessage(content=_ask_for_missing(missing))],
        }
    return {"booking_fields": fields, "awaiting": None}


def route_after_collect_info(state: SchedulingState) -> str:
    if state.get("intent") != "booking":
        return "end_turn"  # abandoned to general conversation
    if state.get("awaiting") == "missing_fields":
        return "end_turn"
    return "validate"