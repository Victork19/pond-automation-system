"""Background job boundary.

Celery is optional for local development. The task functions remain ordinary
Python functions so they can be executed synchronously in tests and workers.
"""
from datetime import datetime, timedelta, timezone
from .db import SessionLocal, CallEvent

try:
    from celery import Celery
    from .core import settings
    celery_app = Celery('pond', broker=settings.redis_url, backend=settings.redis_url)
except ImportError:
    celery_app = None

def _retry_offsets(): return (10, 20, 40)

def schedule_transcript_retries(event_id: str, ends_at: datetime):
    s = SessionLocal()
    try:
        event = s.query(CallEvent).filter_by(event_id=event_id).one_or_none()
        if not event:
            event = CallEvent(event_id=event_id, account='Unknown', ends_at=ends_at, next_attempt_at=ends_at + timedelta(minutes=10))
            s.add(event); s.commit()
        return event.id
    finally: s.close()
