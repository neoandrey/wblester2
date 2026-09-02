"""Diagnostics: service health + recent application logs.

GET /cpanel/jwt/diagnostics  (JWT required, superuser only)
    -> {"generated_at", "services": [...], "logs": [...], "counts": {...}}

The /logs status page renders this payload so an operator can see the state
of every dependent service (API, MongoDB, Redis) and scan warnings/errors
without shelling into the container.
"""

import platform
import time
from datetime import datetime, timezone

import mongoengine
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from ..extensions import jwt as _jwt_ext  # noqa: F401  (kept for clarity)
from ..logging_setup import read_recent_logs
from ..models import Users
from ..utils.auth import _get_user

bp = Blueprint("diagnostics", __name__, url_prefix="/cpanel/jwt")

_STARTED_AT = time.time()


def _superuser() -> bool:
    user: Users | None = _get_user()
    if user is None:
        return False
    from ..models import Roles

    role = Roles.objects(role_id=user.role_id).first()
    return bool(role and role.role_name == "superuser")


def _check_mongo() -> dict:
    start = time.perf_counter()
    try:
        client = mongoengine.get_connection()
        client.admin.command("ping")
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "name": "MongoDB",
            "status": "up",
            "detail": f"ping ok in {latency_ms} ms",
            "latency_ms": latency_ms,
        }
    except Exception as exc:  # pragma: no cover - depends on live mongo
        return {"name": "MongoDB", "status": "down",
                "detail": str(exc)[:200], "latency_ms": None}


def _check_redis(app) -> dict:
    try:
        import redis as redis_lib
    except ImportError:
        # Redis is an optional dependency; report it as not configured
        # rather than letting the endpoint 500.
        return {
            "name": "Redis",
            "status": "not-configured",
            "detail": "redis package not installed",
            "latency_ms": None,
        }

    start = time.perf_counter()
    try:
        client = redis_lib.Redis(
            host=app.config.get("REDIS_HOST", "localhost"),
            port=int(app.config.get("REDIS_PORT", 6379)),
            socket_connect_timeout=2,
            socket_timeout=2,
        ) if not app.config.get("REDIS_USERNAME") else redis_lib.Redis(
            host=app.config.get("REDIS_HOST", "localhost"),
            port=int(app.config.get("REDIS_PORT", 6379)),
            username=app.config.get("REDIS_USERNAME"),
            password=app.config.get("REDIS_PASSWORD"),
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "name": "Redis",
            "status": "up",
            "detail": f"ping ok in {latency_ms} ms",
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        return {
            "name": "Redis",
            "status": "down" if _redis_configured(app) else "not-configured",
            "detail": str(exc)[:200],
            "latency_ms": None,
        }


def _redis_configured(app) -> bool:
    """Redis is optional; treat connection refusals as 'down' only when the
    deployment actually points at a Redis instance."""
    return bool(app.config.get("REDIS_HOST"))


@bp.get("/diagnostics")
@jwt_required()
def diagnostics():
    if not _superuser():
        return jsonify({"message": "Superuser role required"}), 403

    from flask import current_app

    app = current_app._get_current_object()  # type: ignore[attr-defined]
    services = [
        {
            "name": "API",
            "status": "up",
            "detail": (
                f"python {platform.python_version()} | uptime "
                f"{int(time.time() - _STARTED_AT)} s"
            ),
            "latency_ms": 0,
        },
        _check_mongo(),
        _check_redis(app),
    ]

    logs = read_recent_logs(limit=300)
    counts = {
        "error": sum(1 for row in logs if row["level"] == "ERROR"),
        "warning": sum(1 for row in logs if row["level"] == "WARNING"),
    }
    overall = "up"
    if any(s["status"] == "down" for s in services):
        overall = "degraded"
    elif counts["error"]:
        overall = "attention"

    return jsonify(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        overall=overall,
        services=services,
        counts=counts,
        logs=logs,
    )
