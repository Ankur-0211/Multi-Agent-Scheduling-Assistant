"""
check_availability tool. Validates the slot in code (not LLM judgment),
then queries the appointments DB; if taken, suggests up to 3 alternatives
(same day first, then the next working days). Per SDD section 10.
"""
from datetime import timedelta, date as date_cls

from src import config
from src.validation.validators import validate_not_weekend, validate_business_hours, validate_not_past
from src.persistence import appointments_db as db


def _candidate_times() -> list:
    times = []
    for hour in range(config.BUSINESS_HOURS_START, config.BUSINESS_HOURS_END):
        times.append(f"{hour:02d}:00")
        times.append(f"{hour:02d}:30")
    return times


def _next_working_days(start: date_cls, count: int) -> list:
    days = []
    d = start
    while len(days) < count:
        d = d + timedelta(days=1)
        if d.weekday() not in config.NON_WORKING_WEEKDAYS:
            days.append(d)
    return days


def check_availability(date: str, time: str) -> dict:
    for check in (validate_not_weekend(date), validate_business_hours(time), validate_not_past(date, time)):
        if not check["valid"]:
            return {"available": False, "alternatives": [], "error": check["error"]}

    try:
        conn = db.get_connection()
        try:
            if not db.is_slot_taken(conn, date, time):
                return {"available": True, "alternatives": [], "error": None}

            booked_today = db.get_booked_times_for_date(conn, date)
            alternatives = [f"{date}T{t}" for t in _candidate_times() if t not in booked_today][:3]

            if len(alternatives) < 3:
                requested_date = date_cls.fromisoformat(date)
                for next_day in _next_working_days(requested_date, 5):
                    if len(alternatives) >= 3:
                        break
                    booked_next = db.get_booked_times_for_date(conn, next_day.isoformat())
                    for t in _candidate_times():
                        if len(alternatives) >= 3:
                            break
                        if t not in booked_next:
                            alternatives.append(f"{next_day.isoformat()}T{t}")

            return {"available": False, "alternatives": alternatives[:3], "error": None}
        finally:
            conn.close()
    except Exception as e:
        return {"available": False, "alternatives": [], "error": f"Couldn't check availability right now, please try again. ({e})"}