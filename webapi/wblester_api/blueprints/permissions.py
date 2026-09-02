"""Permissions list endpoints."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..models import Permissions
from ..utils.auth import MODIFY, PERM_PERMISSIONS, has_permission
from ..utils.helpers import document_to_dict, log_audit, next_id

bp = Blueprint("permissions_admin", __name__, url_prefix="/cpanel/jwt/permissions")


@bp.get("/")
@bp.get("")
@jwt_required()
def list_permissions():
    permissions = [
        document_to_dict(p) for p in Permissions.objects().order_by("+permission_id")
    ]
    return jsonify({"Permissions": permissions}), 200


@bp.post("/")
@bp.post("")
@jwt_required()
def create_permission():
    if not has_permission(PERM_PERMISSIONS, MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    payload = request.get_json(silent=True) or {}
    if not payload.get("permission_name"):
        return jsonify({"message": "permission_name required"}), 400

    perm = Permissions(
        permission_id=next_id(Permissions, "permission_id"),
        permission_name=payload["permission_name"],
        description=payload.get("description", ""),
    )
    perm.bump_version()
    perm.save()

    log_audit(
        "CREATE",
        "permissions",
        {},
        {"permission_id": perm.permission_id},
        description=f"Created permission '{perm.permission_name}'",
    )
    return jsonify(document_to_dict(perm)), 201
