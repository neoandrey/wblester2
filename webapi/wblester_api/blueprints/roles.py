"""Roles + permissions matrix endpoints."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..models import Permissions, RolePermissions, Roles
from ..utils.auth import MODIFY, PERM_PERMISSIONS, PERM_ROLES, has_permission
from ..utils.helpers import document_to_dict, log_audit, next_id

bp = Blueprint("roles_admin", __name__, url_prefix="/cpanel/jwt/roles")


@bp.get("/")
@bp.get("")
@jwt_required()
def list_roles():
    roles = [document_to_dict(r) for r in Roles.objects().order_by("+role_id")]
    return jsonify({"Roles": roles}), 200


@bp.post("/")
@bp.post("")
@jwt_required()
def create_role():
    if not has_permission(PERM_ROLES, MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    payload = request.get_json(silent=True) or {}
    if not payload.get("role_name"):
        return jsonify({"message": "role_name required"}), 400
    if Roles.objects(role_name=payload["role_name"]).first():
        return jsonify({"message": "Role already exists"}), 409

    role = Roles(
        role_id=next_id(Roles, "role_id"),
        role_name=payload["role_name"],
        description=payload.get("description", ""),
    )
    role.bump_version()
    role.save()
    log_audit("CREATE", "roles", {}, document_to_dict(role))
    return jsonify(document_to_dict(role)), 201


@bp.get("/matrix")
@jwt_required()
def permission_matrix():
    """Full RBAC matrix: every role x every permission with access level."""
    roles = [document_to_dict(r) for r in Roles.objects().order_by("+role_id")]
    permissions = [
        document_to_dict(p) for p in Permissions.objects().order_by("+permission_id")
    ]
    grants = {
        (g.role_id, g.permission_id): g.access_level
        for g in RolePermissions.objects()
    }
    matrix = []
    for role in roles:
        row = {
            "role_id": role["role_id"],
            "role_name": role["role_name"],
            "cells": [],
        }
        for perm in permissions:
            key = (role["role_id"], perm["permission_id"])
            row["cells"].append(
                {
                    "permission_id": perm["permission_id"],
                    "access_level": grants.get(key, -1),
                }
            )
        matrix.append(row)
    return jsonify({"roles": roles, "permissions": permissions, "matrix": matrix}), 200


@bp.put("/matrix/<int:role_id>")
@jwt_required()
def update_role_matrix(role_id: int):
    if not has_permission(PERM_ROLES, MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    payload = request.get_json(silent=True) or {}
    cells = payload.get("cells")
    if not isinstance(cells, list):
        return jsonify({"message": "cells array required"}), 400

    RolePermissions.objects(role_id=role_id).delete()
    for cell in cells:
        try:
            level = int(cell.get("access_level", -1))
        except (TypeError, ValueError):
            level = -1
        if level < 0:
            continue
        RolePermissions(
            role_id=role_id,
            permission_id=int(cell["permission_id"]),
            access_level=level,
        ).save()

    log_audit(
        "UPDATE",
        "role_permissions",
        {"role_id": role_id},
        {"grants": len([c for c in cells if int(c.get("access_level", -1) or -1) >= 0])},
    )
    return jsonify({"message": "Matrix updated"}), 200
