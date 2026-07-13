"""
CRUD for the appointments table -- kept in a SEPARATE SQLite file from
the LangGraph checkpoint DB (data/checkpoints.sqlite), per SDD section 8:
the two kinds of "persistent memory" must not be conflated.
"""
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join("data", "appointments.sqlite")


def get_connection() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    # isolation_level=None -> autocommit mode, so we can issue explicit
    # BEGIN IMMEDIATE / COMMIT / ROLLBACK ourselves (needed for the
    # atomic check-then-write in reserve_slot).
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10, isolation_level=None)
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                purpose TEXT,
                status TEXT NOT NULL DEFAULT 'confirmed',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_appointments_date_time ON appointments (date, time)"
        )
    finally:
        conn.close()


def is_slot_taken(conn: sqlite3.Connection, date: str, time: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM appointments WHERE date = ? AND time = ? AND status = 'confirmed' LIMIT 1",
        (date, time),
    )
    return cur.fetchone() is not None


def get_booked_times_for_date(conn: sqlite3.Connection, date: str) -> set:
    cur = conn.execute(
        "SELECT time FROM appointments WHERE date = ? AND status = 'confirmed'", (date,)
    )
    return {row[0] for row in cur.fetchall()}


def insert_appointment(conn, thread_id, name, email, date, time, purpose) -> int:
    cur = conn.execute(
        """
        INSERT INTO appointments (thread_id, name, email, date, time, purpose, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?)
        """,
        (thread_id, name, email, date, time, purpose, datetime.now().isoformat()),
    )
    return cur.lastrowid