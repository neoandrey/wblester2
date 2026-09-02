"""Scheduler + background mail delivery tests."""


class _StubQueue:
    """Records enqueued dotted-path tasks instead of touching Redis."""

    def __init__(self):
        self.enqueued = []

    def enqueue(self, path, *args, job_id=None, **kwargs):
        self.enqueued.append((path, args, kwargs, job_id))
        return _StubJob(job_id)


class _StubJob:
    def __init__(self, job_id):
        self.id = job_id


def _make_event(event_id=10, with_schedule=True, window="past"):
    from wblester_api.models import Events, Schedules
    from wblester_api.models.documents import utcnow
    from datetime import timedelta

    if with_schedule:
        start = utcnow() - timedelta(days=1)  # past => due now
        end = utcnow() + timedelta(days=30)
        Schedules(
            schedule_id=1,
            name="weekly",
            start_time=start,
            end_time=end,
        ).save()
        params = {"schedule_id": 1, "recipients": ["a@b.com"], "subject": "Hi"}
    else:
        params = {"recipients": ["a@b.com"], "subject": "Hi"}

    ev = Events(
        event_id=event_id,
        event_name=f"Event {event_id}",
        event_type=1,
        parameters=params,
        event_status="OPEN",
        job=None,
    )
    ev.save()
    return ev


def test_scheduler_endpoints_require_superuser(client):
    authorless = client.get("/cpanel/jwt/scheduler/events")
    assert authorless.status_code == 401
    auth = {"Authorization": "Bearer x"}
    resp = client.get("/cpanel/jwt/scheduler/events", headers=auth)
    assert resp.status_code in (401, 422)


def test_scheduler_tick_enqueues_due_event(client, monkeypatch):
    from wblester_api.scheduler import Scheduler

    q = _StubQueue()
    monkeypatch.setattr("wblester_api.worker.get_queue", lambda: q)
    with client.application.app_context():
        _make_event(event_id=10)
        triggered = Scheduler().tick()
    assert triggered == 1
    assert len(q.enqueued) == 1
    path = q.enqueued[0][0]
    assert path == "wblester_api.worker.jobs.run_event"
    assert q.enqueued[0][1] == (10,)


def test_scheduler_skips_future_event(client, monkeypatch):
    from wblester_api.scheduler import Scheduler
    from wblester_api.models.documents import utcnow

    q = _StubQueue()
    monkeypatch.setattr("wblester_api.worker.get_queue", lambda: q)
    with client.application.app_context():
        _make_event(event_id=11, with_schedule=False)
        assert Scheduler().tick() == 0
    assert q.enqueued == []


def test_worker_deliver_mail_calls_send(client, monkeypatch):
    from wblester_api.worker.jobs import deliver_mail

    sent = []
    monkeypatch.setattr(
        "wblester_api.worker.jobs.send_mail",
        lambda recips, subj, html: sent.append((recips, subj, html)),
    )
    with client.application.app_context():
        res = deliver_mail(["a@b.com"], "Subj", "<p>Body</p>")
    assert res["status"] == "sent"
    assert (["a@b.com"], "Subj", "<p>Body</p>") in sent


def test_worker_run_event_records_success_job(client, monkeypatch):
    from wblester_api.models import Jobs, MailTemplates
    from wblester_api.worker.jobs import run_event

    MailTemplates(template_id=1, template_name="mail1", contents="<p>{{name}}</p>").save()
    ev = _make_event(event_id=12)
    ev.mail_template = 1
    ev.parameters = {"recipients": ["a@b.com"], "subject": "Hi", "context": {"name": "Ada"}}
    ev.save()

    sent = []

    def _record(*a, **k):
        sent.append(a)

    monkeypatch.setattr("wblester_api.worker.jobs.send_mail", _record)
    with client.application.app_context():
        outcome = run_event(12)
        job = Jobs.objects(name=f"send:Event 12").first()
    assert outcome["status"] == "sent"
    assert job is not None
    assert job.job_status == Jobs.SUCCEEDED
    assert job.complete is True
    assert sent and "Ada" in sent[0][2]  # linked MailTemplates row rendered


def test_worker_run_event_failure_records_failed_job(client, monkeypatch):
    from wblester_api.models import Jobs
    from wblester_api.worker.jobs import run_event

    import smtplib

    _make_event(event_id=13)
    from wblester_api.models import Events
    ev = Events.objects(event_id=13).first()
    ev.parameters = {"recipients": ["a@b.com"], "subject": "Hi"}
    ev.mail_template = None
    ev.save()

    def boom(*a, **k):
        raise smtplib.SMTPException("down")

    monkeypatch.setattr("wblester_api.worker.jobs.send_mail", boom)
    with client.application.app_context():
        try:
            run_event(13)
        except smtplib.SMTPException:
            pass
        job = Jobs.objects(name="send:Event 13").first()
    assert job is not None
    assert job.job_status == Jobs.FAILED


def test_run_event_endpoint_enqueues(client, monkeypatch):
    from wblester_api.models import Users, Roles

    # Promote admin_test to superuser (role 0) so the endpoint authorizes.
    Users.objects(username="admin_test").update_one(set__role_id=0)
    _make_event(event_id=20)
    q = _StubQueue()
    monkeypatch.setattr("wblester_api.worker.get_queue", lambda: q)

    auth = _admin_token(client)
    resp = client.post("/cpanel/jwt/scheduler/events/20/run", headers=auth)
    assert resp.status_code == 200, resp.get_json()


def _admin_token(client):
    resp = client.post(
        "/auth/login",
        json={"username": "admin_test", "password": "secret123"},
    )
    t = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def test_run_event_endpoint_requires_superuser(client):
    _make_event(event_id=21)
    auth = _admin_token(client)  # admin_test is role 1 (admin), not superuser
    resp = client.post("/cpanel/jwt/scheduler/events/21/run", headers=auth)
    assert resp.status_code == 403


def test_retry_job_requeues(client, monkeypatch):
    from wblester_api.models import Jobs, Users
    from wblester_api.utils.outbox import retry_job

    Users.objects(username="admin_test").update_one(set__role_id=0)
    Jobs(
        job_id="abc123",
        name="send",
        parameters={"recipients": ["a@b.com"], "subject": "Hi", "html": "<p>x</p>"},
        job_status=Jobs.FAILED,
        complete=True,
        errors=["boom"],
        description="Hi",
    ).save()

    q = _StubQueue()
    monkeypatch.setattr("wblester_api.worker.get_queue", lambda: q)
    with client.application.app_context():
        row = retry_job("abc123")
    assert row is not None
    assert row.job_status == Jobs.QUEUED
    assert any(job_id == "abc123" for _, _, _, job_id in q.enqueued)


def test_enqueue_send_mail_uses_correct_path(client, monkeypatch):
    """The one-shot send helper must enqueue a resolvable dotted task path."""
    from wblester_api.worker import enqueue_send_mail

    q = _StubQueue()
    monkeypatch.setattr("wblester_api.worker.get_queue", lambda: q)
    with client.application.app_context():
        jid = enqueue_send_mail(["a@b.com"], "Subj", "<p>Body</p>")
    assert q.enqueued == [("wblester_api.worker.jobs.deliver_mail", (["a@b.com"], "Subj", "<p>Body</p>"), {}, jid)]


def test_scheduler_does_not_redispatch_due_event(client, monkeypatch):
    """A dispatched event moves OFF OPEN so later ticks never re-queue it."""
    from wblester_api.models import Events
    from wblester_api.scheduler import Scheduler

    q = _StubQueue()
    monkeypatch.setattr("wblester_api.worker.get_queue", lambda: q)
    with client.application.app_context():
        _make_event(event_id=30)
        sched = Scheduler()
        first = sched.tick()
        second = sched.tick()
        ev = Events.objects(event_id=30).first()
    assert first == 1
    assert second == 0
    assert len(q.enqueued) == 1
    assert ev.event_status == "QUEUED"


def test_run_event_without_parameters_does_not_crash(client, monkeypatch):
    """An event with no parameters (fired via /run) must not AttributeError."""
    from wblester_api.worker.jobs import run_event

    _make_event(event_id=31, with_schedule=False)
    from wblester_api.models import Events

    ev = Events.objects(event_id=31).first()
    ev.parameters = None
    ev.mail_template = None
    ev.save()

    monkeypatch.setattr(
        "wblester_api.worker.jobs.send_mail",
        lambda recips, subj, html: None,
    )
    with client.application.app_context():
        outcome = run_event(31)
    assert outcome["status"] == "sent"