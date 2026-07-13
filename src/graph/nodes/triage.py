"""
Triage Agent node — classifies intent (general vs booking) using
structured output, and answers general questions directly from the
static FAQ. Per SDD section 13:
- narrow, few-shot prompt
- structured output consumed directly by the conditional edge
- on parse failure, default to 'general' and ask a clarifying question
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src import config
from src.graph.state import SchedulingState


class IntentClassification(BaseModel):
    intent: Literal["general", "booking"] = Field(
        description=(
            "'booking' if the user wants to schedule/book/reserve an appointment, "
            "or mentions a specific date/time for a meeting unprompted. "
            "'general' for any other question (hours, services, greetings, etc.)."
        )
    )
    general_answer: Optional[str] = Field(
        default=None,
        description=(
            "If intent is 'general', a direct, friendly answer to the user's "
            "question using ONLY the FAQ context provided. If intent is "
            "'booking', leave this null — do not answer here."
        ),
    )


TRIAGE_SYSTEM_PROMPT = """You are the Triage Agent for a scheduling assistant.

Your job each turn is to classify the user's message as either:
- "booking": the user wants to schedule, book, or reserve an appointment,
  OR mentions a specific date/time for a meeting unprompted.
- "general": any other question (business hours, services offered, greetings,
  small talk, anything not about creating a new booking).

When in doubt between the two, prefer "booking" — under-triaging a real
booking request is worse than over-triaging a general question, since the
Booking Specialist can still hand back to general conversation later.

If intent is "general", answer the user directly and only using this FAQ:
{faq}
Do not make up information not in the FAQ. If the FAQ doesn't cover it,
say so and offer to help book an appointment instead.

If intent is "booking", leave general_answer null — the Booking Specialist
will take over the conversation.

Examples:
- "What are your hours?" -> general
- "I'd like to book an appointment" -> booking
- "Can you schedule a meeting with me next Tuesday?" -> booking
- "Do you do consultations?" -> general
- "I need to see someone next Friday at 10am" -> booking
- "hey, anyone there?" -> general (greeting/ambiguous small talk, not a booking request)
"""


def _format_faq() -> str:
    return "\n".join(f"- {k}: {v}" for k, v in config.GENERAL_FAQ.items())


def _last_human_message(messages) -> str:
    for m in reversed(messages):
        if getattr(m, "type", None) == "human":
            return m.content
    return ""


def triage_node(state: SchedulingState) -> dict:
    user_text = _last_human_message(state["messages"])

    llm = ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GEMINI_API_KEY,
        thinking_level="low",
        
    )
    structured_llm = llm.with_structured_output(IntentClassification)

    system_prompt = TRIAGE_SYSTEM_PROMPT.format(faq=_format_faq())

    try:
        print(f"[triage] classifying: {user_text!r} ...")
        result = structured_llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_text)]
        )
        intent = result.intent
        answer = result.general_answer
    except Exception as e:
        print(f"[triage] structured output failed ({e}); defaulting to 'general'.")
        intent = "general"
        answer = (
            "Sorry, I didn't quite catch that — are you looking to ask a "
            "question, or would you like to book an appointment?"
        )

    update: dict = {"intent": intent}
    if intent == "general":
        update["messages"] = [AIMessage(content=answer or "Could you rephrase that?")]
    return update


def route_from_triage(state: SchedulingState) -> str:
    return "booking" if state.get("intent") == "booking" else "general_end"