"""
send_booking_notification tool -- webhook POST with a console-log mock
fallback if no NOTIFICATION_WEBHOOK_URL is configured. A failed webhook
never rolls back the booking. Per SDD sections 10 and 15.
"""
import time as time_module
import requests

from src import config


def send_booking_notification(booking_id, name, email, date, time, purpose) -> dict:
    payload = {
        "booking_id": booking_id,
        "name": name,
        "email": email,
        "date": date,
        "time": time,
        "purpose": purpose,
    }

    if not config.NOTIFICATION_WEBHOOK_URL:
        print("=" * 50)
        print("[MOCK NOTIFICATION -- no webhook configured]")
        for k, v in payload.items():
            print(f"  {k}: {v}")
        print("=" * 50)
        return {
            "sent": True,
            "channel": "mock",
            "detail": "No NOTIFICATION_WEBHOOK_URL configured -- payload logged to console instead.",
        }

    last_error = None
    for attempt in range(2):  # one retry
        try:
            resp = requests.post(config.NOTIFICATION_WEBHOOK_URL, json=payload, timeout=10)
            if 200 <= resp.status_code < 300:
                return {"sent": True, "channel": "webhook", "detail": f"POST {resp.status_code} to configured webhook URL"}
            last_error = f"Webhook returned status {resp.status_code}"
        except requests.RequestException as e:
            last_error = str(e)
        if attempt == 0:
            time_module.sleep(1)

    return {"sent": False, "channel": "webhook", "detail": f"Notification failed: {last_error}"}