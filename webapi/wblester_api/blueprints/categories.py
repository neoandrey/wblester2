"""Categories admin endpoints: nested tree for the navigator."""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from ..models import Categories, Pages
from ..utils.helpers import document_to_dict

bp = Blueprint("categories_admin", __name__, url_prefix="/cpanel/jwt/categories")


@bp.get("/tree")
@jwt_required()
def category_tree():
    categories = [
        document_to_dict(c) for c in Categories.objects().order_by("+sort_order")
    ]
    page_counts: dict[int, int] = {}
    for p in Pages.objects.only("category_id"):
        if p.category_id is not None:
            page_counts[p.category_id] = page_counts.get(p.category_id, 0) + 1

    by_id = {c["category_id"]: {**c, "children": [], "page_count": page_counts.get(c["category_id"], 0)} for c in categories}
    roots = []
    for node in by_id.values():
        parent = by_id.get(node.get("parent_id"))
        if parent is not None and parent is not node:
            parent["children"].append(node)
        else:
            roots.append(node)
    return jsonify({"roots": roots}), 200
