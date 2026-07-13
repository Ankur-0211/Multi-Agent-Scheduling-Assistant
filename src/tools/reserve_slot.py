"""
reserve_slot tool -- atomically re-checks availability inside the same
write transaction before inserting, to prevent race conditions between
two near-simultaneous bookings. Per SDD section 10.
"""
import sqlite3

from src.validation.validators import validate_email, validate_not_weekend, validate_business_hours, validate_not_past
from src.persistence import appointments_db as db


def reserve_slot(name: str, email: str, date: str, time: str, purpose: str, thread_id: str) -> dict:
    if not name or not name.strip():
        return {"success": False, "booking_id": None, "error": "Name is required."}
    if not purpose or not purpose.strip():
        return {"success": False, "booking_id": None, "error": "Purpose is required."}

    for check in (
        validate_email(email),
        validate_not_weekend(date),
        validate_business_hours(time),
        validate_not_past(date, time),
    ):
        if not check["valid"]:
            return {"success": False, "booking_id": None, "error": check["error"]}

    conn = db.get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")  # write-locks the DB for this transaction
        if db.is_slot_taken(conn, date, time):
            conn.execute("ROLLBACK")
            return {
                "success": False,
                "booking_id": None,
                "error": f"Sorry, {date} at {time} was just booked by someone else. Please pick another slot.",
            }
        booking_id = db.insert_appointment(conn, thread_id, name.strip(), email.strip(), date, time, purpose.strip())
        conn.execute("COMMIT")
        return {"success": True, "booking_id": booking_id, "error": None}
    except sqlite3.Error as e:
        conn.execute("ROLLBACK")
        return {"success": False, "booking_id": None, "error": f"Booking failed due to a database error, please try again. ({e})"}
    finally:
        conn.close()