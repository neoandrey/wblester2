"""Pages admin endpoints: tree view, visibility, home page assignment."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..models import Categories, Pages, SiteSettings
from ..utils.auth import MODIFY, PERM_PAGES, has_permission
from ..utils.helpers import document_to_dict, log_audit

bp = Blueprint("pages_admin", __name__, url_prefix="/cpanel/jwt/pages")


def _deny(level: int):
    return not has_permission(PERM_PAGES, level)


@bp.get("/tree")
@jwt_required()
def page_tree():
    """Pages grouped under their categories for the admin navigator."""
    categories = [document_to_dict(c) for c in Categories.objects().order_by("+sort_order")]
    pages = [document_to_dict(p) for p in Pages.objects().order_by("+sort_order", "+title")]

    settings = SiteSettings.objects.first()
    home_page_id = getattr(settings, "home_page_id", None) if settings else None
    for page in pages:
        page["is_home"] = page.get("page_id") == home_page_id

    nodes = [
        {"type": "category", **c, "children": [p for p in pages if p.get("category_id") == c["category_id"]]}
        for c in categories
    ]
    root_pages = [p for p in pages if p.get("category_id") is None]
    return jsonify({"categories": categories, "pages": pages, "tree": [*root_pages, *nodes]}), 200


@bp.put("/<int:page_id>/visibility")
@jwt_required()
def set_visibility(page_id: int):
    if _deny(MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    page = Pages.objects(page_id=page_id).first()
    if page is None:
        return jsonify({"message": "Page not found"}), 404
    payload = request.get_json(silent=True) or {}
    old = document_to_dict(page)
    page.visible = bool(payload.get("visible", not page.visible))
    page.bump_version()
    page.save()
    log_audit("UPDATE", "pages", old, document_to_dict(page))
    return jsonify(document_to_dict(page)), 200


@bp.post("/set_home_page/<int:page_id>")
@jwt_required()
def set_home_page(page_id: int):
    if _deny(MODIFY):
        return jsonify({"message": "Permission denied"}), 403
    page = Pages.objects(page_id=page_id).first()
    if page is None:
        return jsonify({"message": "Page not found"}), 404
    settings = SiteSettings.objects.first()
    if settings is None:
        return jsonify({"message": "Site settings missing"}), 500
    old = {"home_page_id": settings.home_page_id}
    settings.home_page_id = page_id
    settings.bump_version()
    settings.save()
    log_audit("UPDATE", "site_settings", old, {"home_page_id": page_id})
    return jsonify({"home_page_id": page_id}), 200
