"""Mailbox endpoints: status transitions, replies and outbound compose."""

import os
import re

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from ..models import Files, Images, MailTemplates, Messages, SiteSettings
from ..models.documents import utcnow
from ..utils.auth import MODIFY, PERM_MESSAGES, has_permission
from ..utils.helpers import document_to_dict, log_audit, next_id
from ..utils.mail import render_template, send_mail

bp = Blueprint("messages_admin", __name__, url_prefix="/cpanel/jwt/messages")

VALID_STATUSES = {0, 1, 2, 3, 4}  # NEW, READ, REPLIED, ARCHIVED, TRASHED

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _resolved_attachments(raw):
    """Map the payload ``attachments`` list to files on disk.

    Each entry is ``{"type": "image"|"file", "id": <int>}`` referencing an
    Images/Files library record. Returns a list of ``(filename, payload,
    mimetype)`` tuples and raises nothing; missing/invalid entries are skipped.
    """
    if not isinstance(raw, list):
        return []
    upload_dir = current_app.config["UPLOAD_DIR"]
    resolved = []
    known = {int(x["id"]): x for x in raw if isinstance(x, dict) and str(x.get("id", "")).isdigit() and x.get("type") in ("image", "file")}
    for key in known:
        kind = known[key]["type"]
        try:
            if kind == "image":
                doc = Images.objects(image_id=key).first()
                filename = doc.file_name if doc else None
                mimetype = doc.image_type if doc else "image/png"
            else:
                doc = Files.objects(file_id=key).first()
                filename = doc.actual_file_name if doc else None
                mimetype = doc.file_type or "application/octet-stream"
        except Exception:  # noqa: BLE001 - skip malformed references
            continue
        if filename is None:
            continue
        path = os.path.join(upload_dir, filename)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as handle:
            payload = handle.read()
        resolved.append((filename, payload, mimetype))
    return resolved


def _plain_to_html(text: str) -> str:
    return "<p>" + (text or "").replace("\n", "<br>") + "</p>"

@bp.get("/unread-count")
@jwt_required()
def unread_count():
    count = Messages.objects(status=Messages.STATUS_NEW).count()
    return jsonify({"count": count}), 200


@bp.post("/compose")
@jwt_required()
def compose_mail():
    """Send outbound HTML mail (optionally rendered from a MailTemplates
    template) and keep a sent copy in the mailbox, linked to any source
    message via ``reply_to_id``."""
    if not has_permission(PERM_MESSAGES, MODIFY):
        return jsonify({"message": "Permission denied"}), 403

    payload = request.get_json(silent=True) or {}
    raw_to = payload.get("to")
    if isinstance(raw_to, str):
        to = [e.strip() for e in raw_to.replace(";", ",").split(",") if e.strip()]
    else:
        to = [e.strip() for e in raw_to if isinstance(e, str) and e.strip()] if raw_to else []
    to = [e for e in to if _EMAIL_RE.match(e)]

    subject = (payload.get("subject") or "").strip()
    body = (payload.get("body") or "").strip()

    if not to:
        return jsonify({"message": "At least one valid recipient is required."}), 400
    if not subject:
        return jsonify({"message": "A subject is required."}), 400

    template_name = (payload.get("template_name") or "").strip()
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    rendered_from_template = ""
    if template_name:
        template = MailTemplates.objects(template_name=template_name).first()
        if template is None:
            return jsonify({"message": f"Template '{template_name}' not found."}), 404
        html = render_template(template.contents, {**context, "body": body})
        rendered_from_template = template_name
    elif body:
        html = body if body.startswith(("<p", "<div", "<html")) else _plain_to_html(body)
    else:
        return jsonify({"message": "body or template_name is required."}), 400

    settings = SiteSettings.objects.first()
    site_name = settings.site_name if settings else "WBLESTER"
    sender = (
        (settings.email if settings and settings.email else "")
        or current_app.config["MAIL_DEFAULT_SENDER"]
    )

    try:
        attachments = _resolved_attachments(payload.get("attachments"))
        send_mail(to, subject, html, attachments)
    except Exception as exc:  # noqa: BLE001 - the outgoing record is still useful
        current_app.logger.warning("Compose mail failed: %s", exc)
        return jsonify({"message": f"Mail delivery failed: {exc}"}), 502

    stored_body = f"[via {rendered_from_template}] " if rendered_from_template else ""
    stored_body += body if body else subject
    if attachments:
        stored_body += (
            f" [attachments: {', '.join(name for name, _, _ in attachments)}]"
        )
    sent = Messages(
        message_id=next_id(Messages, "message_id"),
        from_name=site_name,
        from_email=sender,
        subject=subject,
        body=stored_body,
        status=Messages.STATUS_REPLIED,
        reply_to_id=payload.get("reply_to_id"),
        sent_at=utcnow(),
    )
    sent.save()

    log_audit(
        "CREATE",
        "messages",
        {},
        {"message_id": sent.message_id, "recipients": to},
        description="Mail sent",
    )
    return jsonify(document_to_dict(sent)), 201


@bp.put("/<int:message_id>/status")
@jwt_required()
def set_status(message_id: int):
    if not has_permission(PERM_MESSAGES, MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    message = Messages.objects(message_id=message_id).first()
    if message is None:
        return jsonify({"message": "Message not found"}), 404

    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    if status not in VALID_STATUSES:
        return jsonify({"message": "Invalid status"}), 400

    old = {"status": message.status}
    message.status = int(status)
    message.bump_version()
    message.save()
    log_audit("UPDATE", "messages", old, {"status": message.status})
    return jsonify(document_to_dict(message)), 200


@bp.post("/<int:message_id>/reply")
@jwt_required()
def reply(message_id: int):
    if not has_permission(PERM_MESSAGES, MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    original = Messages.objects(message_id=message_id).first()
    if original is None:
        return jsonify({"message": "Message not found"}), 404

    payload = request.get_json(silent=True) or {}
    body = payload.get("body")
    if not body:
        return jsonify({"message": "body required"}), 400

    settings = SiteSettings.objects.first()
    site_name = settings.site_name if settings else "WBLESTER"
    subject = f"Re: {original.subject}"
    template = MailTemplates.objects(template_name="reply").first()
    html = (
        render_template(template.contents, {"name": original.from_name, "body": body})
        if template
        else f"<p>Dear {original.from_name},</p><p>{body}</p><p>-- {site_name}</p>"
    )

    try:
        send_mail([original.from_email], subject, html)
    except Exception as exc:  # noqa: BLE001 - reply is recorded even if mail fails
        current_app.logger.warning("Reply mail failed: %s", exc)
        return jsonify({"message": f"Mail delivery failed: {exc}"}), 502

    reply_msg = Messages(
        message_id=next_id(Messages, "message_id"),
        from_name=site_name,
        from_email=(settings.email if settings else "") or "no-reply@wblester.local",
        subject=subject,
        body=body,
        status=Messages.STATUS_REPLIED,
        reply_to_id=original.message_id,
        sent_at=utcnow(),
    )
    reply_msg.save()

    original.status = Messages.STATUS_REPLIED
    original.bump_version()
    original.save()

    log_audit(
        "CREATE",
        "messages",
        {},
        {"message_id": reply_msg.message_id, "reply_to": original.message_id},
        description="Reply sent",
    )
    return jsonify(document_to_dict(reply_msg)), 201
