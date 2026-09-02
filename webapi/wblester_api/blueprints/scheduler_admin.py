"""Events + Jobs manager for the admin portal.

Provides list + run-now + retry so the Flutter Events/Jobs page can drive the
background scheduler from the WebApi without shelling into a container.

- GET  /cpanel/jwt/scheduler/events
- GET  /cpanel/jwt/scheduler/jobs
- POST /cpanel/jwt/scheduler/events/<id>/run
- POST /cpanel/jwt/scheduler/jobs/<job_id>/retry
All scoped to superuser (the admin portal guards the nav; the API enforces).
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from ..models import Events, Jobs, RolePermissions, Roles, Users
from ..utils.helpers import document_to_dict

bp = Blueprint("scheduler_admin", __name__, url_prefix="/cpanel/jwt/scheduler")


def _is_superuser() -> bool:
    from ..utils.auth import _get_user

    user: Users | None = _get_user()
    if user is None:
        return False
    role = Roles.objects(role_id=user.role_id).first()
    return bool(role and role.role_name == "superuser")


@bp.get("/events")
@jwt_required()
def list_events():
    if not _is_superuser():
        return jsonify({"message": "Superuser role required"}), 403
    events = [document_to_dict(e) for e in Events.objects().order_by("-event_id")]
    return jsonify({"Events": events}), 200


@bp.post("/events/<int:event_id>/run")
@jwt_required()
def run_event(event_id: int):
    if not _is_superuser():
        return jsonify({"message": "Superuser role required"}), 403
    event = Events.objects(event_id=event_id).first()
    if event is None:
        return jsonify({"message": "Event not found"}), 404
    try:
        from ..worker import enqueue_event_job

        jid = enqueue_event_job(event_id)
        return jsonify({"message": "Event enqueued", "job": jid}), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({"message": f"Enqueue failed: {exc}"}), 502


@bp.get("/jobs")
@jwt_required()
def list_jobs():
    if not _is_superuser():
        return jsonify({"message": "Superuser role required"}), 403
    jobs = [document_to_dict(j) for j in Jobs.objects().order_by("-start_time")]
    return jsonify({"Jobs": jobs}), 200


@bp.post("/jobs/<job_id>/retry")
@jwt_required()
def retry_job(job_id: str):
    if not _is_superuser():
        return jsonify({"message": "Superuser role required"}), 403
    try:
        from ..utils.outbox import retry_job

        row = retry_job(job_id)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"message": f"Retry failed: {exc}"}), 502
    if row is None:
        return jsonify({"message": "Job not found"}), 404
    return jsonify({"message": "Job re-queued", "job": document_to_dict(row)}), 200