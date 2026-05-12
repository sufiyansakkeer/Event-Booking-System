from celery import Celery
from app.core.config import get_settings

settings = get_settings()
# Create the Celery application instance.
# The first argument is the name of the current module — used by Celery
# for naming tasks internally. Think of this like your app's bundle ID.
celery_app = Celery(
    "event_booking",
    # The broker is where tasks are SENT TO. (while published)
    # Celery publishes a message here when you call .delay() or .apply_async().
    # Redis acts like a queue — producer (FastAPI) writes, consumer (worker) reads.
    # In Dart terms: broker = StreamController, task = event added to the stream.
    broker=settings.REDIS_URL,
    # The backend is where RESULTS are STORED after a task finishes.
    # When a worker finishes a task, it writes the result back to Redis.
    # You can then call AsyncResult(task_id).get() to retrieve it.
    backend=settings.REDIS_URL,
    # Tell Celery where your task functions live.
    # Without this, Celery won't know which functions to register as tasks.
    include=["app.tasks.email_tasks"],
)

# Configuration applied directly on the app instance.
celery_app.conf.update(
    # Serialize task arguments and results as JSON.
    # Default is pickle which is a security risk — always use JSON.
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # If a task result is not fetched within 1 hour, delete it from Redis.
    # Prevents Redis from filling up with forgotten results.
    result_expires=3600,
    # Use UTC for all task timestamps — avoids timezone bugs.
    timezone="UTC",
    enable_utc=True,
)
