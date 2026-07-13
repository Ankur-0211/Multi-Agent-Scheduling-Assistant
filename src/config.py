"""
Central place for env vars, business rules, and static FAQ content.
Per the SDD, business hours/weekend policy are configurable here,
and there is a single LLM provider (Gemini) with no dual-provider abstraction.
"""
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-3.5-flash"

# Business hours policy (used later by validation/availability nodes too)
BUSINESS_HOURS_START = 9   # 9 AM
BUSINESS_HOURS_END = 18    # 6 PM
NON_WORKING_WEEKDAYS = {5, 6}  # Python weekday(): Mon=0 ... Sat=5, Sun=6

# Small static FAQ — deliberately not a vector store; retrieval is Assignment 1's concern.
GENERAL_FAQ = {
    "hours": "We're open Monday to Friday, 9 AM to 6 PM (IST). Closed weekends.",
    "services": "We offer consultations, follow-up appointments, and general inquiries.",
    "booking": "You can book an appointment right here in this chat — just tell me your preferred date and time.",
}


def validate_config():
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://aistudio.google.com/apikey"
        )