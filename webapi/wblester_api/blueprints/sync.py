"""Sync contract endpoints consumed by the Flutter DataSyncService.

Contract:
- GET /cpanel/jwt/sync/cpanel/<Table>[?since_version=N|since_date=ISO]
      -> {"<Table>": [record...]}  records use snake_case keys.
- GET /cpanel/jwt/sync/update/cpanel?q={"<Table>":[id,...]}
      -> {"<Table>": [record...]} full rows for the requested ids.

Deltas are computed from ``current_version`` / ``last_modified_date``
mirroring the sync configuration in the drift layer.
"""

import json

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..models import TABLE_REGISTRY
from ..utils.helpers import document_to_dict

bp = Blueprint("sync", __name__, url_prefix="/cpanel/jwt/sync")


@bp.get("/cpanel/<table>")
@jwt_required()
def sync_table(table: str):
    doc_class = TABLE_REGISTRY.get(table)
    if doc_class is None:
        return jsonify({"message": f"Unknown table '{table}'"}), 404

    query = {}
    since_version = request.args.get("since_version", type=int)
    since_date = request.args.get("since_date")
    if since_version is not None:
        query["current_version__gt"] = since_version
    if since_date:
        parsed = _parse_date(since_date)
        if parsed is not None:
            query["last_modified_date__gt"] = parsed

    docs = doc_class.objects(**query).order_by(_id_field(doc_class))
    records = [document_to_dict(d) for d in docs]
    return jsonify({table: records}), 200


@bp.get("/update/cpanel")
@jwt_required()
def fetch_updates():
    raw = request.args.get("q")
    if not raw:
        return jsonify({"message": "Missing q parameter"}), 400
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return jsonify({"message": "Invalid JSON in q parameter"}), 400

    result = {}
    for table, ids in payload.items():
        doc_class = TABLE_REGISTRY.get(table)
        if doc_class is None or not isinstance(ids, list):
            result[table] = []
            continue
        id_field = _id_field(doc_class)
        docs = doc_class.objects(**{f"{id_field}__in": ids})
        result[table] = [document_to_dict(d) for d in docs]
    return jsonify(result), 200


def _id_field(doc_class) -> str:
    """The external integer/uuid id field of a document class."""
    if hasattr(doc_class, "job_id"):
        return "job_id"
    for candidate in (
        "settings_id",
        "user_id",
        "role_id",
        "permission_id",
        "image_id",
        "file_id",
        "account_id",
        "template_id",
        "type_id",
        "event_id",
        "schedule_id",
        "trigger_id",
        "category_id",
        "page_id",
        "message_id",
    ):
        if hasattr(doc_class, candidate):
            return candidate
    return "id"


def _parse_date(value: str):
    from datetime import datetime

    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
