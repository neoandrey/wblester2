"""RQ task handlers (executed inside the worker process)."""

from flask import current_app

from ..models import Events, Jobs, MailTemplates, Messages, SiteSettings
from ..models.documents import utcnow
from ..utils.mail import render_template, send_mail


def deliver_mail(recipients, subject, html) -> dict:
    """Low-level unconditional send. Called by retryable jobs and one-shot sends."""
    recipients = [r for r in (recipients or []) if r]
    if not recipients:
        return {"status": "skipped", "reason": "no recipients"}
    return _smtp_send(recipients, subject, html)


def send_templated(recipients, subject, template_body, context=None) -> dict:
    """Render a template then send, as a retryable RQ job."""
    html = render_template(template_body, (context or {}))
    return _smtp_send(recipients, subject, html)


def run_event(event_id: int) -> dict:
    """Execute a scheduled Event: render its linked mail template and send.

    RQ retries the whole call on failure, which is what makes failed sends
    retryable at the transport level. The Mongo outbox row is marked FAILED
    before the exception propagates so the admin portal can drive a manual
    retry via the Jobs manager.
    """
    event = _find_event(event_id)
    if event is None:
        current_app.logger.warning("run_event: event %s not found", event_id)
        _mark(outcome="failed", reason="event not found")
        return {"ok": False, "reason": "event not found"}

    settings = SiteSettings.objects.first()
    recipients = (event.parameters or {}).get("recipients", [])
    subject = (event.parameters or {}).get("subject") or f"Scheduled: {event.event_name}"
    template = _find_template(event.mail_template)
    context = dict((event.parameters or {}).get("context", {}))
    html = render_template(template.contents, context) if template else "<p>Scheduled content.</p>"

    job_row = _outbox_job(event, recipients, subject)
    try:
        outcome = _smtp_send(recipients, subject, html)
    except Exception as exc:  # noqa: BLE001
        _fail_job(job_row, str(exc))
        raise
    _finish_job(job_row, outcome)

    if event.job_history is None:
        event.job_history = []
    event.job_history.append(str(job_row["job_id"]))
    event.bump_version()
    event.save()
    return outcome


def _smtp_send(recipients, subject, html) -> dict:
    try:
        send_mail(recipients, subject, html)
        return {"status": "sent", "to": recipients}
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error("send failed: %s", exc)
        raise


def _find_event(event_id):
    if not event_id:
        return None
    try:
        return Events.objects(event_id=int(event_id)).first()
    except Exception:
        return None


def _find_template(template_id):
    if not template_id:
        return None
    try:
        return MailTemplates.objects(template_id=int(template_id)).first()
    except Exception:
        return None


def _outbox_job(event, recipients, subject) -> Jobs:
    import uuid

    row = Jobs(
        job_id=f"event-{event.event_id}-{uuid.uuid4().hex[:8]}",
        name=f"send:{event.event_name}",
        parameters={"recipients": recipients, "subject": subject, "event_id": event.event_id},
        description=f"Scheduled mail for event #{event.event_id}",
        job_status=Jobs.RUNNING,
        start_time=utcnow(),
        complete=False,
    )
    try:
        row.save()
    except Exception:
        pass
    return row


def _finish_job(row, outcome):
    try:
        if outcome.get("status") == "sent":
            row.job_status = Jobs.SUCCEEDED
            row.complete = True
            row.info = ["sent"]
        else:
            row.job_status = Jobs.SUCCEEDED
            row.complete = True
            row.info = ["skipped", outcome.get("reason", "")]
        row.end_time = utcnow()
        row.save()
    except Exception:
        pass


def _fail_job(row, reason):
    try:
        row.job_status = Jobs.FAILED
        row.complete = True
        row.end_time = utcnow()
        row.errors = [reason]
        row.save()
    except Exception:
        pass


def _mark(outcome="failed", reason=""):
    try:
        import uuid

        Jobs(
            job_id=f"event-missing-{uuid.uuid4().hex[:8]}",
            name="run_event",
            job_status=Jobs.FAILED,
            errors=[reason],
            info=[outcome],
            complete=True,
            start_time=utcnow(),
        ).save()
    except Exception:
        pass