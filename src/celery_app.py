"""
Celery application instance and Beat schedule for the TTAB pipeline.

The Beat schedule fires download_task daily at 06:00 UTC; that task
chains parse_task → enrich_task on success.

Run worker:  celery -A src.celery_app worker --loglevel=info
Run beat:    celery -A src.celery_app beat   --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

from src.settings import get as get_setting

app = Celery(
    "ttab",
    broker=get_setting("redis", "url", "redis://localhost:6379/0"),
    backend=get_setting("redis", "url", "redis://localhost:6379/0"),
    include=["src.tasks"],
)

app.conf.timezone = "UTC"

app.conf.beat_schedule = {
    "daily-pipeline": {
        "task": "src.tasks.download_task",
        "schedule": crontab(hour=6, minute=0),
        "kwargs": {"days": 1},
    },
}


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Initialize the database schema when the worker starts."""
    from src.database import init_db

    init_db()
