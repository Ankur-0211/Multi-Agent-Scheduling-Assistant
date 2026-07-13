"""
Phase 4 manual verification -- exercises all three tools directly,
outside the graph. Books a slot, attempts a duplicate (should be
rejected), and fires a mock notification.
"""
import uuid
from datetime import datetime, timedelta

from src.persistence.appointments_db import init_db
from src.tools.check_availability import check_availability
from src.tools.reserve_slot import reserve_slot
from src.tools.send_booking_notification import send_booking_notification


def next_weekday_date(days_ahead_min=1):
    d = datetime.now().date() + timedelta(days=days_ahead_min)
    while d.weekday() >= 5:
        d = d + timedelta(days=1)
    return d.isoformat()


def main():
    init_db()
    test_date = next_weekday_date()
    test_time = "15:00"
    thread_id = f"phase4-test-{uuid.uuid4()}"

    print(f"Testing with date={test_date}, time={test_time}\n")

    print("1) Checking availability (should be available)...")
    avail = check_availability(test_date, test_time)
    print(f"   {avail}\n")
    assert avail["available"] is True

    print("2) Reserving the slot...")
    result = reserve_slot(name="Ankur Test", email="ankur@example.com", date=test_date,
                           time=test_time, purpose="Consultation", thread_id=thread_id)
    print(f"   {result}\n")
    assert result["success"] is True
    booking_id = result["booking_id"]

    print("3) Checking availability again (should now be unavailable, with alternatives)...")
    avail2 = check_availability(test_date, test_time)
    print(f"   {avail2}\n")
    assert avail2["available"] is False
    assert len(avail2["alternatives"]) > 0

    print("4) Attempting a DUPLICATE booking on the same slot (should be rejected)...")
    dup = reserve_slot(name="Someone Else", email="someone@example.com", date=test_date,
                        time=test_time, purpose="Another consultation", thread_id=str(uuid.uuid4()))
    print(f"   {dup}\n")
    assert dup["success"] is False

    print("5) Firing the mock notification...")
    notif = send_booking_notification(booking_id=booking_id, name="Ankur Test", email="ankur@example.com",
                                       date=test_date, time=test_time, purpose="Consultation")
    print(f"   {notif}\n")
    assert notif["sent"] is True

    print("All Phase 4 checks passed.")


if __name__ == "__main__":
    main()