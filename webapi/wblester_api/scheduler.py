"""rq-scheduler implementation: turn due Events into enqueued RQ jobs.

The compose ``worker --scheduler`` process runs this loop. Each tick looks at
scheduled Events whose run window has passed and are not yet dispatched, then
enqueues their send to the RQ ``default`` queue. Because RQ retries failed
jobs, failed sends automatically stay retryable; the admin portal can also
force a re-run from the Events/Jobs manager.
"""

from datetime import datetime, timedelta, timezone

from .models import Events, Schedules
from .models.documents import utcnow


class Scheduler:
    def __init__(self, window_minutes: int = 0):
        self.window_minutes = window_minutes

    def tick(self) -> int:
        """Dispatch any due events. Returns the number enqueued."""
        now = utcnow()
        dispatched = 0
        for event in Events.objects(event_status="OPEN"):
            if not self._is_due(event, now):
                continue
            from .worker import enqueue_event_job

            enqueue_event_job(event.event_id)
            # Mark dispatched so the next tick does not re-enqueue the send
            # every poll cycle (10s) and flood the queue with duplicates.
            event.event_status = "QUEUED"
            event.save()
            dispatched += 1
        return dispatched

    def _is_due(self, event, now) -> bool:
        # Without a linked schedule or an explicit run time, never fire.
        if event.job:
            try:
                return now >= self._parse(event.job)
            except Exception:
                return False

        sched = None
        if event.parameters:
            sid = event.parameters.get("schedule_id")
            if sid:
                sched = self._find_schedule(sid)
        if sched is None:
            return False
        if sched.start_time and now < sched.start_time:
            return False
        if sched.end_time and now >= sched.end_time:
            return False
        return True

    def _find_schedule(self, sid):
        try:
            return Schedules.objects(schedule_id=int(sid)).first()
        except Exception:
            return None

    @staticmethod
    def _parse(value):
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        text = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return utcnow() - timedelta(days=365 * 10)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt