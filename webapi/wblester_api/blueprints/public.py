"""Public (unauthenticated) endpoints: contact form + website content."""

from flask import Blueprint, current_app, jsonify, request
from mongoengine.errors import ValidationError

from ..models import (
    Categories,
    MailTemplates,
    Messages,
    Pages,
    SiteSettings,
)
from ..models.documents import utcnow
from ..utils.helpers import log_audit, next_id, snake_to_camel
from ..utils.mail import render_template, send_mail

bp = Blueprint("public", __name__, url_prefix="/public")

_SETTINGS_PUBLIC_FIELDS = (
    "site_name",
    "site_title",
    "site_description",
    "address",
    "email",
    "phone_number",
    "contact_us_message",
    "google_map",
    "social_media",
    "home_page_id",
)


@bp.get("/content")
def content():
    """One anonymous round-trip that feeds the website's offline cache.

    Returns every visible category and page (with content blocks) plus the
    public subset of site settings. The SPA stores this in IndexedDB,
    renders from cache first and revalidates periodically.
    """
    categories = [
        _camel_doc(c, (
            "category_id", "parent_id", "category_name", "slug",
            "sort_order",
        ))
        for c in Categories.objects(visible=True).order_by(
            "sort_order", "category_id"
        )
    ]
    settings_doc = SiteSettings.objects.first()
    settings = {}
    home_page_id = getattr(settings_doc, "home_page_id", None) if settings_doc else None
    page_docs = list(
        Pages.objects(visible=True).order_by("sort_order", "page_id")
    )
    # The configured landing page is always published, even if an editor
    # toggled it invisible — the website cannot render without it.
    if (
        home_page_id is not None
        and not any(p.page_id == home_page_id for p in page_docs)
    ):
        hidden_home = Pages.objects(page_id=home_page_id).first()
        if hidden_home:
            page_docs.append(hidden_home)
    pages = [
        _camel_doc(p, (
            "page_id", "category_id", "parent_id", "title", "slug",
            "sort_order", "seo_title", "seo_description", "content_json",
        ))
        for p in page_docs
    ]
    if settings_doc:
        settings = {
            snake_to_camel(k): getattr(settings_doc, k)
            for k in _SETTINGS_PUBLIC_FIELDS
        }
    return jsonify({
        "categories": categories,
        "pages": pages,
        "settings": settings,
        "fetchedAt": utcnow().isoformat(),
    })


def _camel_doc(doc, fields):
    return {
        snake_to_camel(f): getattr(doc, f)
        for f in fields
        if hasattr(doc, f)
    }


@bp.post("/contact")
def contact():
    data = request.get_json(silent=True) or {}
    required = ("name", "email", "subject", "body")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(
            {"message": f"Missing required fields: {', '.join(missing)}"}
        ), 400

    message = Messages(
        message_id=next_id(Messages, "message_id"),
        from_name=data["name"],
        from_email=data["email"],
        subject=data["subject"],
        body=data["body"],
        status=Messages.STATUS_NEW,
        sent_at=utcnow(),
    )
    try:
        message.save()
    except ValidationError as exc:
        return jsonify({"message": str(exc)}), 400

    _notify_mailing_list(message)
    log_audit("CREATE", "messages", {}, {"message_id": message.message_id})

    return jsonify({"message": "Message received"}), 201


def _notify_mailing_list(message: Messages) -> None:
    settings = SiteSettings.objects.first()
    recipients = list(settings.mailing_list or []) if settings else []
    template = MailTemplates.objects(template_name="contact").first()

    subject = f"[{settings.site_name if settings else 'WBLESTER'}] {message.subject}"
    context = {
        "name": message.from_name,
        "email": message.from_email,
        "subject": message.subject,
        "body": message.body,
    }
    body = (
        render_template(template.contents, context)
        if template
        else f"<p>From: {message.from_name} &lt;{message.from_email}&gt;</p>"
        f"<p>{message.body}</p>"
    )
    try:
        send_mail(recipients, subject, body)
    except Exception as exc:  # noqa: BLE001 - mail must never break the form
        current_app.logger.warning("Contact notification failed: %s", exc)
