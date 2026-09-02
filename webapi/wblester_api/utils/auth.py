"""Authentication and RBAC helpers.

RBAC matrix enforced server-side:
- guest            -> read-only            (level 0)
- superuser, admin -> read + modify        (level 1)
- admin            -> create + delete      (level 2)
"""

from functools import wraps

from flask import current_app, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from ..models import Permissions, RolePermissions, Roles, Users
from .helpers import document_to_dict

# Permission names used across the API.
PERM_PAGES = "pages"
PERM_CATEGORIES = "categories"
PERM_SETTINGS = "settings"
PERM_USERS = "users"
PERM_ROLES = "roles"
PERM_PERMISSIONS = "permissions"
PERM_MESSAGES = "messages"
PERM_FILES = "files"
PERM_AUDIT = "audit_trail"

READ = 0
MODIFY = 1
CREATE_DELETE = 2


def _get_user():
    """Resolve the JWT identity to a Users document (or None)."""
    identity = get_jwt_identity()
    if identity is None:
        return None
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return Users.objects(user_id=user_id).first()


def role_access_level(role_id: int) -> int:
    """Highest access level granted to a role. superuser always wins."""
    role = Roles.objects(role_id=role_id).first()
    if role and role.role_name == "superuser":
        return CREATE_DELETE
    levels = RolePermissions.objects(role_id=role_id).only("access_level")
    return max((lvl.access_level for lvl in levels), default=-1)


def permission_id_map() -> dict:
    return {p.permission_name: p.permission_id for p in Permissions.objects()}


def has_permission(
    permission_name: str,
    required_level: int,
    user: Users | None = None,
) -> bool:
    user = user or _get_user()
    if user is None:
        return False
    role = Roles.objects(role_id=user.role_id).first()
    if role is None:
        return False
    if role.role_name == "superuser":
        return True
    perm = Permissions.objects(permission_name=permission_name).first()
    if perm is None:
        return False
    grant = RolePermissions.objects(
        role_id=user.role_id,
        permission_id=perm.permission_id,
        access_level__gte=required_level,
    ).first()
    return grant is not None


def require_permission(permission_name: str, required_level: int):
    """Decorator enforcing JWT auth plus the RBAC matrix."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return jsonify({"message": "Missing or invalid token"}), 401
            user = _get_user()
            if user is None:
                return jsonify({"message": "Unknown user"}), 401
            if user.locked or not user.active:
                return jsonify({"message": "Account locked or inactive"}), 403
            if not has_permission(permission_name, required_level, user):
                return jsonify({"message": "Permission denied"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def login_user(username: str, password: str):
    """Validate credentials honoring lockout columns. Returns (user, error)."""
    user = Users.objects(username=username).first()
    if user is None:
        return None, "Invalid credentials"
    max_attempts = current_app.config["MAX_LOGIN_ATTEMPTS"]
    if user.locked or (user.login_attempts or 0) >= max_attempts:
        if not user.locked:
            user.locked = True
            user.save()
        return None, "Account locked"
    if not user.check_password(password):
        user.login_attempts = (user.login_attempts or 0) + 1
        if user.login_attempts >= max_attempts:
            user.locked = True
        user.save()
        return None, "Invalid credentials"

    user.login_attempts = 0
    user.locked = False
    user.login_count = (user.login_count or 0) + 1
    user.connection_status = True
    user.active = True
    user.save()
    return user, None


def user_payload(user: Users) -> dict:
    data = document_to_dict(user)
    data.pop("password_hash", None)
    data.pop("password_history", None)
    data.pop("token", None)
    role = Roles.objects(role_id=user.role_id).first()
    data["role_name"] = role.role_name if role else None
    if role is not None and role.role_name == "superuser":
        data["permissions"] = [p.permission_name for p in Permissions.objects()]
    else:
        grants = RolePermissions.objects(role_id=user.role_id).only("permission_id")
        perm_ids = {g.permission_id for g in grants}
        data["permissions"] = [
            p.permission_name
            for p in Permissions.objects(permission_id__in=list(perm_ids))
        ]
    return data
