"""SMTP helpers kept thin so tests can monkeypatch ``send_mail``."""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app


def render_template(template_body: str, context: dict) -> str:
    """Tiny {{placeholder}} substitution for MailTemplates contents."""
    body = template_body or ""
    for key, value in (context or {}).items():
        body = body.replace("{{" + key + "}}", str(value))
    return body


def send_mail(
    recipients,
    subject: str,
    html_body: str,
    attachments: list | None = None,
) -> None:
    """Send an HTML email through the configured SMTP server.

    ``attachments`` is an optional list of ``(filename, payload, mimetype)``
    tuples; payload is bytes. In dev mode (no SMTP credentials) the mail is
    logged as a dry run.
    """
    recipients = [r for r in recipients if r]
    if not recipients:
        return

    app = current_app._get_current_object()
    host = app.config["SMTP_HOST"]
    port = app.config["SMTP_PORT"]
    username = app.config.get("SMTP_USERNAME")
    password = app.config.get("SMTP_PASSWORD")
    sender = app.config["MAIL_DEFAULT_SENDER"]

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(html_body, "html", "utf-8"))

    for filename, payload, mimetype in attachments or []:
        part = MIMEApplication(payload or b"", _subtype=_mime_subtype(mimetype))
        part.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(part)

    if not username or not password:
        # Dev mode without SMTP credentials: log instead of send.
        app.logger.info(
            "MAIL (dry-run) to=%s subject=%s attachments=%d",
            recipients,
            subject,
            len(attachments or []),
        )
        return

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(sender, recipients, message.as_string())


def _mime_subtype(mimetype: str | None) -> str:
    if not isinstance(mimetype, str) or "/" not in mimetype:
        return "octet-stream"
    return (mimetype.split("/", 1)[1] or "octet-stream").lower()
