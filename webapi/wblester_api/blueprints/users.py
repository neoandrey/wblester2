"""User management endpoints (password handling + lock/unlock)."""

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from ..models import Roles, Users
from ..utils.auth import (
    CREATE_DELETE,
    MODIFY,
    PERM_USERS,
    has_permission,
    user_payload,
)
from ..utils.helpers import document_to_dict, log_audit, next_id
from ..utils.mail import send_mail

bp = Blueprint("users_admin", __name__, url_prefix="/cpanel/jwt/users")

PROTECTED_FIELDS = {"password_hash", "password_history", "token"}


@bp.get("/<int:user_id>")
@jwt_required()
def get_user(user_id: int):
    if not has_permission(PERM_USERS, MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    user = Users.objects(user_id=user_id).first()
    if user is None:
        return jsonify({"message": "User not found"}), 404
    return jsonify(user_payload(user)), 200


@bp.post("/")
@bp.post("")
@jwt_required()
def create_user():
    if not has_permission(PERM_USERS, CREATE_DELETE):
        return jsonify({"message": "Permission denied"}), 403
    payload = request.get_json(silent=True) or {}
    password = payload.pop("password", None)
    if not payload.get("username") or not password or not payload.get("email"):
        return jsonify({"message": "username, email and password are required"}), 400
    if Users.objects(username=payload["username"]).first():
        return jsonify({"message": "Username already exists"}), 409

    user = Users(
        user_id=next_id(Users, "user_id"),
        username=payload["username"],
        email=payload["email"],
        must_change_password=True,
    )
    _apply_fields(user, payload)
    user.set_password(password)
    user.password_history = [user.password_hash]
    user.bump_version()
    user.save()

    role_name = "Superuser"
    role = Roles.objects(role_id=user.role_id).first()
    if role is not None:
        role_name = role.role_name

    panel_url = current_app.config.get("PANEL_URL") or "/admin"
    _notify_user_created(
        recipients=[user.email],
        username=user.username,
        role_name=role_name,
        panel_url=panel_url,
    )

    data = user_payload(user)
    log_audit("CREATE", "users", {}, document_to_dict(user))
    return jsonify(data), 201


def _notify_user_created(recipients, username, role_name, panel_url):
    """Send a notification that an account was created (never the password)."""
    try:
        send_mail(
            recipients,
            "Your WBLester account has been created",
            (
                "<p>Hello <b>{username}</b>,</p>"
                "<p>An administrator has created your account on "
                "<b>WBLester</b> (role: <i>{role}</i>).</p>"
                "<p>You will be asked to set a new password on your first "
                "login.</p>"
                "<p>Sign in here: <a href=\"{panel}\">{panel}</a></p>"
            ).format(username=username, role=role_name, panel=panel_url),
        )
    except Exception:  # pragma: no cover - notification must not block creation
        current_app.logger.warning("notification email failed for %s", username)


@bp.put("/<int:user_id>")
@jwt_required()
def update_user(user_id: int):
    if not has_permission(PERM_USERS, MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    user = Users.objects(user_id=user_id).first()
    if user is None:
        return jsonify({"message": "User not found"}), 404

    payload = request.get_json(silent=True) or {}
    old = document_to_dict(user)
    old.pop("password_hash", None)
    _apply_fields(user, payload)
    user.bump_version()
    user.save()

    new = document_to_dict(user)
    new.pop("password_hash", None)
    log_audit("UPDATE", "users", old, new)
    return jsonify(user_payload(user)), 200


@bp.put("/<int:user_id>/password")
@jwt_required()
def change_password(user_id: int):
    user = Users.objects(user_id=user_id).first()
    if user is None:
        return jsonify({"message": "User not found"}), 404

    from flask_jwt_extended import get_jwt_identity

    is_self = str(get_jwt_identity()) == str(user_id)
    if not is_self and not has_permission(PERM_USERS, MODIFY):
        return jsonify({"message": "Permission denied"}), 403

    payload = request.get_json(silent=True) or {}
    new_password = payload.get("new_password")
    if not new_password:
        return jsonify({"message": "new_password required"}), 400
    if is_self and not user.check_password(payload.get("current_password", "")):
        return jsonify({"message": "Current password incorrect"}), 401

    user.set_password(new_password)
    history = list(user.password_history or [])
    history.append(user.password_hash)
    user.password_history = history[-10:]
    user.login_attempts = 0
    user.locked = False
    # A self-imposed change satisfies the forced-change requirement; an admin
    # resetting a password re-arms it so the next login must change it again.
    user.must_change_password = False if is_self else True
    user.bump_version()
    user.save()
    log_audit("UPDATE", "users", {}, {"user_id": user_id}, description="password change")
    return jsonify({"message": "Password updated"}), 200


@bp.post("/<int:user_id>/unlock")
@jwt_required()
def unlock_user(user_id: int):
    if not has_permission(PERM_USERS, MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    user = Users.objects(user_id=user_id).first()
    if user is None:
        return jsonify({"message": "User not found"}), 404
    user.locked = False
    user.login_attempts = 0
    user.bump_version()
    user.save()
    log_audit("UPDATE", "users", {}, {"locked": False, "user_id": user_id})
    return jsonify(user_payload(user)), 200


def _apply_fields(user: Users, payload: dict) -> None:
    for key, value in payload.items():
        snake = key
        if key != key.lower():
            from ..utils.helpers import camel_to_snake

            snake = camel_to_snake(key)
        if snake in PROTECTED_FIELDS or snake == "id":
            continue
        if snake in ("username", "email") and not value:
            continue
        if hasattr(user, snake):
            setattr(user, snake, value)
