# Multi Agent Scheduling Assistant

A multi-agent scheduling assistant built with **LangGraph**, orchestrating a **Triage Agent**
(routes general Q&A vs. booking requests) and a **Booking Specialist** (owns the full,
multi-turn appointment-booking lifecycle: collect → validate → check availability →
reserve → notify → confirm).

Built as Assignment 2 of a 5-day AI internship project (Assignment 1 was a RAG-based
customer support agent; this project shifts orchestration from LangChain chains to
LangGraph's stateful graph model, since this assignment requires genuine multi-agent
branching and durable, refresh-proof conversational state).

## Live Demo
🔗 **Live URL**: _(added after deployment — see Deployment section below)_

## Features
- **Two-agent LangGraph routing**: a Triage Agent classifies each message (`general` vs
  `booking`) via structured LLM output, not free-text parsing.
- **Conversational, incremental booking**: asks only for missing fields (name, email,
  date, time, purpose), never re-asks for known ones.
- **Real date/time normalization**: wraps `dateparser`, with explicit fixes for known
  parser limitations (`"next Friday"`, hedge words like `"around 2pm"`) discovered during
  development — see `docs/architecture.md` for details.
- **Code-enforced validation**: business hours, weekends, past-dates, email format, and
  double-booking are all validated in Python, not left to LLM judgment.
- **Persistent, refresh-proof memory**: LangGraph's `SqliteSaver` checkpointer, keyed by a
  `thread_id` stored in the browser's URL — a hard page refresh (or a fresh tab with the
  same URL) resumes the exact same conversation and in-progress booking state.
- **Mock notification**: webhook POST (webhook.site/Pipedream) with a console-logged
  fallback if no webhook URL is configured.
- **Quota-resilient**: if the selected Gemini model hits its rate limit/quota, the UI
  shows a clear alert (not a generic error) and lets you switch models instantly from
  the sidebar to continue.

## Tech Stack
| Component | Choice |
|---|---|
| Language | Python 3.12 |
| Orchestration | LangGraph 0.6.7 (`StateGraph` + conditional edges) |
| LLM | Gemini 3.5 Flash (default), with Gemini 2.5 Flash / 2.5 Flash-Lite as switchable fallbacks — via `langchain-google-genai` |
| Persistent memory | LangGraph `SqliteSaver` checkpointer, keyed by `thread_id` |
| Appointments DB | Separate SQLite file/table (`data/appointments.sqlite`) |
| Date/time parsing | `dateparser`, with custom preprocessing fixes |
| Frontend | Streamlit |
| Notification | Webhook POST, console-log fallback |

## Project Structure
scheduling-assistant/
├── app.py                          # Streamlit entrypoint
├── requirements.txt
├── .env.example
├── data/
│   ├── checkpoints.sqlite          # LangGraph conversation checkpoints
│   └── appointments.sqlite         # Booking records
├── src/
│   ├── config.py                   # Env vars, business hours, static FAQ
│   ├── graph/
│   │   ├── state.py                 # SchedulingState schema
│   │   ├── builder.py               # StateGraph wiring
│   │   └── nodes/                   # triage, collect_info, validation,
│   │                                 # availability, reservation, notification, confirmation
│   ├── tools/                       # check_availability, reserve_slot, send_booking_notification
│   ├── persistence/                 # appointments_db.py (CRUD)
│   ├── validation/                  # datetime_parser.py, validators.py
│   └── utils/                       # llm_helpers.py (content extraction, quota detection)
├── tests/
│   ├── test_datetime_parser.py
│   ├── test_validators.py
│   ├── test_tools.py (via test_phase4_tools.py, run manually)
│   └── test_graph_routing.py
└── docs/
├── architecture.md
└── workflow.md

## Setup & Local Run
```bash
git clone <your-repo-url>
cd scheduling-assistant
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in GEMINI_API_KEY
streamlit run app.py
```

## Environment Variables
| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Free key from https://aistudio.google.com/apikey |
| `NOTIFICATION_WEBHOOK_URL` | No | webhook.site/Pipedream URL; if unset, notifications are logged to the console instead |

## Running Tests
```bash
python -m pytest tests/ -v
```
Covers: date/time normalization edge cases, field validators, and full graph-routing
integration tests (LLM mocked deterministically — no API cost, no real data touched).

## Deployment (Streamlit Community Cloud)
1. Push this repo to a public GitHub repository.
2. Go to https://share.streamlit.io → "New app" → connect your GitHub repo, branch, and `app.py`.
3. Under the app's **Secrets**, add:
```toml
   GEMINI_API_KEY = "your-key-here"
   NOTIFICATION_WEBHOOK_URL = "your-webhook-url-or-leave-blank"
```
4. Deploy, then verify the live URL: have a full conversation, refresh the page, and
   confirm it resumes correctly (this is the one thing that must be checked on the
   **live** deployment specifically, not just locally).

## Known Limitations
- **Ephemeral disk on free-tier hosting**: Streamlit Community Cloud does not guarantee
  persistent disk across app restarts/redeploys. `data/checkpoints.sqlite` and
  `data/appointments.sqlite` may reset when the app redeploys or sleeps and wakes.
  Acceptable for this demo-scoped assignment; a production version would use a hosted
  DB (e.g. Postgres) instead.
- No reschedule/cancel flow — booking creation only.
- One active thread per browser tab; no multi-thread switcher UI.
- Single fixed timezone (IST assumed); no multi-timezone support.
- Business hours (Mon–Fri, 9 AM–6 PM) are configurable in `src/config.py` but not
  user-facing/per-tenant.
