import time
from typing import Any

from celery import Task
from app.core.celery_app import celery_app


# @celery_app.task turns a regular function into a Celery task.
# bind=True gives the task access to `self`, which lets you call
# self.retry(). celery stores task-related methods inside the self
# if something fails — like a retry interceptor in Dio.
# max_retries=3 means if it fails, Celery will retry up to 3 times.
# default_retry_delay=60 means wait 60 seconds between retries.
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_booking_confirmation_email(
    self: "Task[..., Any]", user_email: str, event_name: str, booking_id: int
) -> None:
    """
    Simulates sending a booking confirmation email.
    In production, replace the print with SendGrid / SES / SMTP call.
    """
    try:
        # Simulate network latency of an email provider API call.
        # This is why it must be a background task — you never want
        # a 2-second email API call blocking your HTTP response.
        print(
            f"[EMAIL TASK] Sending confirmation to {user_email} for '{event_name}'..."
        )
        time.sleep(2)  # simulate slow email API

        print(f"[EMAIL TASK] ✅ Email sent to {user_email} | Booking ID: {booking_id}")

    except Exception as exc:
        # If anything goes wrong, tell Celery to retry this task.
        # exc=exc passes the original exception so Celery logs it properly.
        # raise self.retry() stops current execution and reschedules the task.
        raise self.retry(exc=exc) from exc
