"""Dashboard statistics: asset + content counts for the admin overview.

GET /cpanel/jwt/stats  (JWT required, any authenticated role)
    -> {"generated_at", "webapi": {...}, "backend": {...}, "frontend": {...}}
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from ..models import (
    AuditTrail,
    Categories,
    EventTriggers,
    EventTypes,
    Events,
    Files,
    FrontendLog,
    GMailAccounts,
    IMAPAccounts,
    Images,
    Jobs,
    MailTemplates,
    Messages,
    Pages,
    Permissions,
    RolePermissions,
    Roles,
    Schedules,
    SiteSettings,
    Users,
)

bp = Blueprint("stats", __name__, url_prefix="/cpanel/jwt/stats")


def _as_int(value) -> int:
    try:
        return int(str(value or 0))
    except (TypeError, ValueError):
        return 0


@bp.get("")
@bp.get("/")
@jwt_required()
def stats():
    storage = sum(_as_int(i.file_size) for i in Images.objects().only("file_size"))
    storage += sum(_as_int(f.file_size) for f in Files.objects().only("file_size"))
    variants = sum(len(i.variants or {}) for i in Images.objects().only("variants"))

    messages = Messages.objects()
    frontend_errors = FrontendLog.objects(level="ERROR").count()

    sync_mode = None
    settings = SiteSettings.objects().only("sync_mode").first()
    if settings is not None:
        sync_mode = settings.sync_mode

    webapi = {
        "users": Users.objects().count(),
        "active_users": Users.objects(active=True).count(),
        "locked_users": Users.objects(locked=True).count(),
        "must_change_password": Users.objects(must_change_password=True).count(),
        "roles": Roles.objects().count(),
        "permissions": Permissions.objects().count(),
        "role_permissions": RolePermissions.objects().count(),
        "logins": sum(u.login_count or 0 for u in Users.objects().only("login_count")),
        "audit_trail": AuditTrail.objects().count(),
    }

    backend = {
        "pages": Pages.objects().count(),
        "categories": Categories.objects().count(),
        "messages": messages.count(),
        "messages_new": messages(status=Messages.STATUS_NEW).count(),
        "mail_templates": MailTemplates.objects().count(),
        "events": Events.objects().count(),
        "event_types": EventTypes.objects().count(),
        "event_triggers": EventTriggers.objects().count(),
        "schedules": Schedules.objects().count(),
        "jobs": Jobs.objects().count(),
        "jobs_running": Jobs.objects(job_status=Jobs.RUNNING).count(),
        "gmail_accounts": GMailAccounts.objects().count(),
        "imap_accounts": IMAPAccounts.objects().count(),
        "sync_mode": sync_mode,
    }

    frontend = {
        "images": Images.objects().count(),
        "files": Files.objects().count(),
        "storage_bytes": storage,
        "image_variants": variants,
        "frontend_logs": FrontendLog.objects().count(),
        "frontend_errors": frontend_errors,
    }

    return jsonify(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        webapi=webapi,
        backend=backend,
        frontend=frontend,
    )