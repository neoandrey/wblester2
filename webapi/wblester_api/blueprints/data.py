"""Generic data endpoints backing BaseRepository fetches and admin pushes.

Contract (matches the Flutter repositories):
- GET    /cpanel/jwt/data/<Table>?q={"<table_lower>":{...}}&startIndex=&limit=
- POST   /cpanel/jwt/data/<Table>          create/upsert (camelCase body)
- PUT    /cpanel/jwt/data/<Table>/<id>     update
- DELETE /cpanel/jwt/data/<Table>/<id>     delete

Writes bump ``current_version``, stamp ``last_modified_date`` and append an
AuditTrail entry, so the admin UI can pull the change into the local drift
database via its sync flow.
"""

import json

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..models import TABLE_ID_FIELDS, TABLE_REGISTRY, Users
from ..utils.auth import (
    CREATE_DELETE,
    MODIFY,
    PERM_AUDIT,
    PERM_CATEGORIES,
    PERM_FILES,
    PERM_MESSAGES,
    PERM_PAGES,
    PERM_PERMISSIONS,
    PERM_ROLES,
    PERM_SETTINGS,
    PERM_USERS,
    has_permission,
)
from ..utils.helpers import (
    apply_payload,
    camel_to_snake,
    document_to_dict,
    log_audit,
    next_id,
)
from ..models.documents import utcnow

bp = Blueprint("data", __name__, url_prefix="/cpanel/jwt/data")

# Table -> (permission name, write level, delete level). Read is open to any
# authenticated user.
TABLE_PERMISSIONS = {
    "Pages": (PERM_PAGES, MODIFY, CREATE_DELETE),
    "Categories": (PERM_CATEGORIES, MODIFY, CREATE_DELETE),
    "SiteSettings": (PERM_SETTINGS, MODIFY, CREATE_DELETE),
    "Users": (PERM_USERS, MODIFY, CREATE_DELETE),
    "Roles": (PERM_ROLES, MODIFY, CREATE_DELETE),
    "Permissions": (PERM_PERMISSIONS, MODIFY, CREATE_DELETE),
    "Messages": (PERM_MESSAGES, MODIFY, MODIFY),
    "MailTemplates": (PERM_MESSAGES, MODIFY, CREATE_DELETE),
    "Images": (PERM_FILES, MODIFY, CREATE_DELETE),
    "Files": (PERM_FILES, MODIFY, CREATE_DELETE),
    "AuditTrail": (PERM_AUDIT, MODIFY, CREATE_DELETE),
}

FALLBACK_PERM = PERM_PAGES

def _id_field(doc_class) -> str:
    """Resolve the external id field from the explicit table map.

    Never probe by attribute order: Pages carries both category_id and
    page_id, and a naive hasattr() scan used to pick the wrong one.
    """
    for table, cls in TABLE_REGISTRY.items():
        if cls is doc_class:
            field = TABLE_ID_FIELDS.get(table)
            if field:
                return field
    return "id"


def _guard(table: str, level: int):
    """Runtime RBAC check. Returns an error response or None."""
    doc_class = TABLE_REGISTRY.get(table)
    if doc_class is None:
        return jsonify({"message": f"Unknown table '{table}'"}), 404
    perm_name = TABLE_PERMISSIONS.get(table, (FALLBACK_PERM,))[0]
    if not has_permission(perm_name, level):
        return jsonify({"message": "Permission denied"}), 403
    return None


def _actor():
    user = Users.objects(user_id=int(get_jwt_identity())).first()
    return user


@bp.get("/<table>")
@jwt_required()
def get_records(table: str):
    doc_class = TABLE_REGISTRY.get(table)
    if doc_class is None:
        return jsonify({"message": f"Unknown table '{table}'"}), 404

    filters = _parse_filters(request.args.get("q"))
    query = {k: v for k, v in filters.items() if k in doc_class._fields_ordered}
    docs = doc_class.objects(**query)

    start = request.args.get("startIndex", type=int) or 0
    limit = request.args.get("limit", type=int) or 0
    if start or limit:
        docs = docs.skip(start).limit(limit)

    docs = docs.order_by(_id_field(doc_class))
    return jsonify({table: [document_to_dict(d) for d in docs]}), 200


@bp.post("/<table>")
@jwt_required()
def upsert_record(table: str):
    denied = _guard(table, MODIFY)
    if denied:
        return denied
    doc_class = TABLE_REGISTRY.get(table)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"message": "JSON object body required"}), 400

    id_field = _id_field(doc_class)
    from ..utils.helpers import snake_to_camel

    record_id = (
        payload.get(id_field)
        or payload.get(snake_to_camel(id_field))
        or payload.get("id")
    )
    actor = _actor()

    if record_id:
        existing = doc_class.objects(**{id_field: _coerce_id(record_id)}).first()
        if existing is not None:
            old_data = document_to_dict(existing)
            apply_payload(existing, payload)
            existing.bump_version()
            existing.save()
            log_audit(
                "UPDATE", table.lower(), old_data, document_to_dict(existing),
                username=actor.username if actor else None,
                user_id=actor.user_id if actor else None,
            )
            return jsonify(document_to_dict(existing)), 200

    doc = doc_class()
    apply_payload(doc, payload)
    if not getattr(doc, id_field, None):
        setattr(doc, id_field, next_id(doc_class, id_field))
    doc.bump_version()
    doc.created_datetime = utcnow()
    doc.save()
    new_data = document_to_dict(doc)
    log_audit(
        "CREATE", table.lower(), {}, new_data,
        username=actor.username if actor else None,
        user_id=actor.user_id if actor else None,
    )
    return jsonify(new_data), 201


@bp.put("/<table>/<record_id>")
@jwt_required()
def update_record(table: str, record_id):
    denied = _guard(table, MODIFY)
    if denied:
        return denied
    doc_class = TABLE_REGISTRY.get(table)
    id_field = _id_field(doc_class)
    doc = doc_class.objects(**{id_field: _coerce_id(record_id)}).first()
    if doc is None:
        return jsonify({"message": f"{table} not found"}), 404

    payload = request.get_json(silent=True) or {}
    old_data = document_to_dict(doc)
    apply_payload(doc, payload)
    doc.bump_version()
    doc.save()

    actor = _actor()
    log_audit(
        "UPDATE", table.lower(), old_data, document_to_dict(doc),
        username=actor.username if actor else None,
        user_id=actor.user_id if actor else None,
    )
    return jsonify(document_to_dict(doc)), 200


@bp.delete("/<table>/<record_id>")
@jwt_required()
def delete_record(table: str, record_id):
    denied = _guard(table, CREATE_DELETE)
    if denied:
        return denied
    doc_class = TABLE_REGISTRY.get(table)
    id_field = _id_field(doc_class)
    doc = doc_class.objects(**{id_field: _coerce_id(record_id)}).first()
    if doc is None:
        return jsonify({"message": f"{table} not found"}), 404

    old_data = document_to_dict(doc)
    doc.delete()

    actor = _actor()
    log_audit(
        "DELETE", table.lower(), old_data, {},
        username=actor.username if actor else None,
        user_id=actor.user_id if actor else None,
    )
    return jsonify({"message": "Deleted"}), 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_filters(raw):
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict) and len(payload) == 1:
        inner = next(iter(payload.values()))
        if isinstance(inner, dict):
            return inner
    if isinstance(payload, dict):
        return payload
    return {}


def _coerce_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value
