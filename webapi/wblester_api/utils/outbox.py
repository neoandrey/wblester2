"""Retryable templated mail sends (outbox-backed).

These helpers live in the WebApi process and persist a MongoDB ``Jobs`` row,
then enqueue the actual SMTP send to Redis. The RQ worker retries the send
itself on transport failure; the admin portal's Jobs manager exposes a
``POST /retry`` to re-queue any that ultimately failed.

Outbox sends are used for scheduled event mail and for admin-initiated templated
sends. Replies and one-shot sends still go straight through ``send_mail``.
"""

import uuid

from flask import current_app

from ..models import Jobs
from ..models.documents import utcnow


def enqueue_templated_send(recipients, subject, template_body, context=None, name="send") -> Jobs:
    """Persist an outbox job and enqueue its delivery. Returns the Jobs row."""
    import html as _html

    from ..worker import get_queue

    from .mail import render_template

    html_body = render_template(template_body, (context or {}))
    job_id = f"{name}-{uuid.uuid4().hex[:12]}"

    row = Jobs(
        job_id=job_id,
        name=name,
        parameters={
            "recipients": recipients,
            "subject": subject,
            "html": _html.escape(html_body)[:2000],
        },
        description=subject,
        job_status=Jobs.QUEUED,
        start_time=utcnow(),
        complete=False,
    )
    row.save()

    try:
        queue = get_queue()
        queue.enqueue(
            "wblester_api.worker.jobs.deliver_mail",
            recipients,
            subject,
            html_body,
            job_id=job_id,
            job_timeout=60,
        )
        return row
    except Exception as exc:  # noqa: BLE001 - Redis may be down at boot
        current_app.logger.error("enqueue failed: %s", exc)
        row.job_status = Jobs.FAILED
        row.errors = [str(exc)]
        row.complete = True
        row.save()
        return row


def retry_job(job_id: str) -> Jobs | None:
    """Re-queue a previously enqueued job whose RQ job failed."""
    from ..worker import get_queue

    row = Jobs.objects(job_id=job_id).first()
    if row is None:
        return None

    import json as _json

    params = row.parameters or {}
    recipients = params.get("recipients") or []
    subject = params.get("subject") or row.description or "Scheduled message"
    html = params.get("html") or "<p>Scheduled message</p>"

    queue = get_queue()
    queue.enqueue(
        "wblester_api.worker.jobs.deliver_mail",
        recipients,
        subject,
        html,
        job_id=row.job_id,
        job_timeout=60,
    )
    row.job_status = Jobs.QUEUED
    row.complete = False
    row.errors = []
    row.save()
    return row