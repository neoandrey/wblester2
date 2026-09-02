"""Auth blueprint: JWT access + refresh tokens."""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)

from ..models import AuditTrail, Roles, Users
from ..utils.auth import login_user, user_payload

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/login")
@bp.post("/jwt_login")  # legacy alias used by earlier app builds
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    # M2M bootstrap credentials come from environment configuration.
    if (
        username == current_app.config["SYNC_API_USERNAME"]
        and password == current_app.config["SYNC_API_PASSWORD"]
        and username
        and password
    ):
        m2m = Users.objects(username=username).first()
        if m2m is None:
            role = Roles.objects(role_name="admin").first()
            m2m = Users(
                user_id=_next_user_id(),
                username=username,
                email=f"{username}@internal.local",
                role_id=role.role_id if role else 0,
                active=True,
            )
            m2m.set_password(password)
            m2m.save()
        access = create_access_token(identity=str(m2m.user_id))
        refresh = create_refresh_token(identity=str(m2m.user_id))
        return jsonify(access_token=access, refresh_token=refresh), 200

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    user, error = login_user(username, password)
    if user is None:
        AuditTrail(
            description=f"Failed login attempt for '{username}'",
            change_type="LOGIN_FAILED",
            affected_table="users",
            username=username,
            old_data={},
            new_data={},
        ).save()
        return jsonify({"message": error}), 401

    access = create_access_token(identity=str(user.user_id))
    refresh = create_refresh_token(identity=str(user.user_id))
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        seconds=current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    )
    return jsonify(
        access_token=access,
        refresh_token=refresh,
        expires_at=expires.isoformat(),
        user=user_payload(user),
    ), 200


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    user = Users.objects(user_id=int(identity)).first()
    if user is None or user.locked:
        return jsonify({"message": "Unknown user"}), 401
    access = create_access_token(identity=str(user.user_id))
    new_refresh = create_refresh_token(identity=str(user.user_id))
    return jsonify(access_token=access, refresh_token=new_refresh), 200


def _next_user_id() -> int:
    highest = Users.objects.order_by("-user_id").first()
    return highest.user_id + 1 if highest else 1
