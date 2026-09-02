"""Contact form and mailbox reply tests."""

from wblester_api.models import Messages


def _auth(client):
    token = client.post(
        "/auth/login", json={"username": "admin_test", "password": "secret123"}
    ).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_contact_creates_new_message(client, monkeypatch):
    sent = {}
    monkeypatch.setattr(
        "wblester_api.blueprints.public.send_mail",
        lambda recipients, subject, body: sent.update(
            recipients=list(recipients), subject=subject, body=body
        ),
    )

    resp = client.post(
        "/public/contact",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "subject": "Hello",
            "body": "Interested in your services.",
        },
    )
    assert resp.status_code == 201, resp.get_json()

    message = Messages.objects().first()
    assert message is not None
    assert message.status == Messages.STATUS_NEW
    assert message.from_email == "jane@example.com"
    assert sent["subject"].endswith("Hello")


def test_contact_validates_required_fields(client):
    resp = client.post("/public/contact", json={"name": "Only Name"})
    assert resp.status_code == 400
    assert "email" in resp.get_json()["message"]


def test_reply_updates_status_and_sends_mail(client, monkeypatch):
    original = Messages(
        message_id=1,
        from_name="Jane",
        from_email="jane@example.com",
        subject="Question",
        body="?",
        status=Messages.STATUS_NEW,
    ).save()

    sent = {}
    monkeypatch.setattr(
        "wblester_api.blueprints.messages.send_mail",
        lambda recipients, subject, body: sent.update(
            recipients=list(recipients), subject=subject, body=body
        ),
    )

    resp = client.post(
        "/cpanel/jwt/messages/1/reply",
        json={"body": "Here is the answer."},
        headers=_auth(client),
    )
    assert resp.status_code == 201, resp.get_json()
    assert sent["recipients"] == ["jane@example.com"]

    reply = Messages.objects(reply_to_id=1).first()
    assert reply is not None and reply.status == Messages.STATUS_REPLIED

    original.reload()
    assert original.status == Messages.STATUS_REPLIED


def test_status_transition(client):
    msg = Messages(
        message_id=2,
        from_name="Bob",
        from_email="bob@example.com",
        subject="Hi",
        body="Test body",
    ).save()

    resp = client.put(
        "/cpanel/jwt/messages/2/status",
        json={"status": 3},
        headers=_auth(client),
    )
    assert resp.status_code == 200
    msg.reload()
    assert msg.status == 3  # ARCHIVED

def test_compose_sends_outbound_mail(client, monkeypatch):
    from wblester_api.models import MailTemplates, SiteSettings

    MailTemplates(template_id=1, template_name="newsletter", contents="<p>Hello {{name}}: {{body}}</p>").save()
    SiteSettings(settings_id=1, site_name="WBLESTER", site_title="WBLester",
                 email="office@wblester.local").save()

    sent = {}
    monkeypatch.setattr(
        "wblester_api.blueprints.messages.send_mail",
        lambda recipients, subject, body, attachments=None: sent.update(
            recipients=list(recipients), subject=subject, body=body,
            attachments=attachments,
        ),
    )

    resp = client.post(
        "/cpanel/jwt/messages/compose",
        json={
            "to": ["one@example.com", "two@example.org", "bad-address"],
            "subject": "Harvest update",
            "body": "Crops are in.",
            "template_name": "newsletter",
            "context": {"name": "Farmer"},
            "reply_to_id": 7,
        },
        headers=_auth(client),
    )
    assert resp.status_code == 201, resp.get_json()
    assert sent["recipients"] == ["one@example.com", "two@example.org"]
    assert "Harvest update" in sent["subject"]
    assert "Hello Farmer" in sent["body"]
    assert "Crops are in." in sent["body"]

    out = Messages.objects(reply_to_id=7).first()
    assert out is not None and out.status == Messages.STATUS_REPLIED


def test_compose_requires_recipients_and_subject(client):
    resp = client.post(
        "/cpanel/jwt/messages/compose",
        json={"to": [], "subject": "", "body": "hi"},
        headers=_auth(client),
    )
    assert resp.status_code == 400


def test_compose_unknown_template_404(client):
    resp = client.post(
        "/cpanel/jwt/messages/compose",
        json={"to": ["a@b.co"], "subject": "S", "template_name": "nope"},
        headers=_auth(client),
    )
    assert resp.status_code == 404
