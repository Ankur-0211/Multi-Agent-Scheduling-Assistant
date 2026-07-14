"""
Notification Node -- calls send_booking_notification(). A failed
notification never rolls back the reservation. Per SDD section 15.
"""
from src.graph.state import SchedulingState
from src.tools.send_booking_notification import send_booking_notification


def notification_node(state: SchedulingState) -> dict:
    fields = state["booking_fields"]
    result = send_booking_notification(
        booking_id=fields["booking_id"], name=fields["name"], email=fields["email"],
        date=fields["date"], time=fields["time"], purpose=fields["purpose"],
    )
    return {"notification_status": "sent" if result["sent"] else "failed"}