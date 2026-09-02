"""Site settings singleton endpoints."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..models import SiteSettings
from ..utils.auth import MODIFY, PERM_SETTINGS, has_permission
from ..utils.helpers import document_to_dict, log_audit

bp = Blueprint("settings_admin", __name__, url_prefix="/cpanel/jwt/settings")


@bp.get("/")
@bp.get("")
@jwt_required()
def get_settings():
    settings = SiteSettings.objects.first()
    if settings is None:
        return jsonify({"message": "Settings not initialized"}), 404
    data = document_to_dict(settings)
    # Secrets never leave the server.
    data.pop("decryption_password", None)
    data.pop("secret_key", None)
    return jsonify(data), 200


@bp.put("/")
@bp.put("")
@jwt_required()
def update_settings():
    if not has_permission(PERM_SETTINGS, MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    settings = SiteSettings.objects.first()
    if settings is None:
        return jsonify({"message": "Settings not initialized"}), 404

    payload = request.get_json(silent=True) or {}
    old = document_to_dict(settings)

    from ..utils.helpers import apply_payload

    apply_payload(settings, payload)
    settings.bump_version()
    settings.save()

    new = document_to_dict(settings)
    new.pop("decryption_password", None)
    new.pop("secret_key", None)
    log_audit("UPDATE", "site_settings", old, new)
    return jsonify(new), 200
