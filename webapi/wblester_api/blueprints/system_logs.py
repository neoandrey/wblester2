"""SIEM-style consolidated log endpoint + frontend log ingestion.

GET  /cpanel/jwt/logs           (superuser only) merged stream from
                                 webapi log file, backend AuditTrail and
                                 browser-reported FrontendLog rows.
POST /cpanel/jwt/logs/frontend  (any authenticated token) ingest a
                                 browser-side event for the merged view.
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..logging_setup import read_recent_logs
from ..models import AuditTrail, FrontendLog, Roles, Users
from ..utils.auth import _get_user

bp = Blueprint("system_logs", __name__, url_prefix="/cpanel/jwt/logs")

_LEVELS = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR"}
_MAX_MESSAGE = 2000


def _superuser() -> bool:
    user: Users | None = _get_user()
    if user is None:
        return False
    role = Roles.objects(role_id=user.role_id).first()
    return bool(role and role.role_name == "superuser")


def _norm_level(level: str) -> str:
    level = (level or "").upper()
    if level == "WARNING":
        return "WARN"
    return level if level in _LEVELS else ""


def _webapi_rows(limit: int) -> list[dict]:
    return [
        {
            "source": "webapi",
            "ts": row["ts"],
            "level": _norm_level(row["level"]),
            "page": row.get("logger", ""),
            "message": row.get("message", ""),
            "username": "",
        }
        for row in read_recent_logs(limit=limit)
    ]


def _backend_rows(limit: int) -> list[dict]:
    rows = AuditTrail.objects().order_by("-change_time").limit(limit)
    out = []
    for row in rows:
        message = row.description or "{} on {}".format(
            row.change_type or "",
            row.affected_table or "",
        )
        ts = row.change_time
        out.append(
            {
                "source": "backend",
                "ts": ts.isoformat(sep=" ") if hasattr(ts, "isoformat") else str(ts),
                "level": "INFO",
                "page": row.affected_table or "",
                "message": message,
                "username": row.username or "",
            }
        )
    return out


def _frontend_rows(limit: int) -> list[dict]:
    rows = FrontendLog.objects().order_by("-created_at").limit(limit)
    out = []
    for row in rows:
        ts = row.created_at
        out.append(
            {
                "source": "frontend",
                "ts": ts.isoformat(sep=" ") if hasattr(ts, "isoformat") else str(ts),
                "level": _norm_level(row.level),
                "page": row.page or "",
                "message": row.message or "",
                "username": row.username or "",
            }
        )
    return out


@bp.get("")
@bp.get("/")
@jwt_required()
def consolidated_logs():
    if not _superuser():
        return jsonify({"message": "Superuser role required"}), 403

    source = request.args.get("source", "all")
    level = _norm_level(request.args.get("level", ""))
    try:
        limit = min(int(request.args.get("limit", 200)), 500)
    except (TypeError, ValueError):  # pragma: no cover - bad input
        limit = 200
    if limit < 1:
        limit = 200

    rows: list[dict] = []
    if source in ("all", "webapi"):
        rows.extend(_webapi_rows(limit))
    if source in ("all", "backend"):
        rows.extend(_backend_rows(limit))
    if source in ("all", "frontend"):
        rows.extend(_frontend_rows(limit))

    if level and level != "ALL":
        wanted = {"WARNING", "WARN"} if level in ("WARNING", "WARN") else {level}
        rows = [r for r in rows if r["level"] in wanted]

    # ISO-style timestamps sort lexicographically; empties sink to the bottom.
    rows.sort(key=lambda r: (r["ts"] or "", r["source"]), reverse=True)
    rows = rows[:limit]

    counts = {
        "error": sum(1 for r in rows if r["level"] == "ERROR"),
        "warning": sum(1 for r in rows if r["level"] == "WARN"),
        "info": sum(1 for r in rows if r["level"] == "INFO"),
    }
    return jsonify(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        counts=counts,
        logs=rows,
    )


@bp.post("/frontend")
@jwt_required()
def ingest_frontend_log():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message") or "").strip()
    if not message:
        return jsonify({"message": "message is required"}), 400

    context = payload.get("context")
    if not isinstance(context, dict):
        context = {}

    entry = FrontendLog(
        level=_norm_level(payload.get("level", "INFO")) or "INFO",
        message=message[:_MAX_MESSAGE],
        page=str(payload.get("page") or "")[:_MAX_MESSAGE],
        context=context,
        username=str(get_jwt_identity() or ""),
    )
    entry.save()
    return jsonify({"message": "logged"}), 201