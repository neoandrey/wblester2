"""Upload endpoints: images and files stored on disk + metadata documents.

Uploads are restricted to safe, site-owned content: raster/vector images for
the Images collection, and documents (pdf/office/text) for the Files
collection. Deletion is dependency-aware — a referenced asset cannot be
removed while pages still use its URL.
"""

import mimetypes
import os
import re
import uuid

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    send_from_directory,
)
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..models import Files, Images, Pages, Users
from ..utils.auth import CREATE_DELETE, PERM_FILES, has_permission
from ..utils.helpers import document_to_dict, log_audit, next_id
from ..utils.images import generate_variants, resolve_variant_media

bp = Blueprint("uploads", __name__, url_prefix="/cpanel/jwt/uploads")

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

#: Allowed upload content. Extension is the primary gate; content type is a
#: fast secondary check for images. SVG is intentionally excluded: its
#: embedded script/foreign-object capability makes untrusted SVG an XSS vector.
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
FILE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".csv", ".rtf",
}
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}

#: Per-upload size cap in bytes (independent of the global MAX_CONTENT_LENGTH).
UPLOAD_MAX_BYTES = 10 * 1024 * 1024


def _safe_name(name: str) -> str:
    base = os.path.basename(name or "file")
    return _SAFE_NAME_RE.sub("_", base) or "file"


def _clear_file(upload_dir: str, *names: str) -> None:
    """Best-effort removal of an uploaded file and its on-disk derivatives."""
    for name in names:
        if not name:
            continue
        try:
            path = os.path.join(upload_dir, name)
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass


def _variant_names(stored_name: str) -> list[str]:
    stem, ext = os.path.splitext(stored_name)
    return [
        f"{stem}.{variant}.{out_ext}"
        for variant in ("lg", "md", "sm", "thumb")
        for out_ext in ("jpg", "png")
    ]


def _asset_used(value, url: str, stem: str) -> bool:
    if not isinstance(value, str):
        return False
    if value == url:
        return True
    if stem and value.startswith("/uploads/"):
        return value.split("/", 2)[2] == stem or value.split("/", 2)[2].startswith(stem + ".")
    return stem and f"/uploads/{stem}." in value


def _page_refs(url: str, stem: str) -> list[dict]:
    """Pages whose block content embeds this asset (direct or variant URL)."""
    refs = []
    for page in Pages.objects():
        if _scan(page.content_json, url, stem):
            refs.append(
                {"page_id": page.page_id, "title": page.title, "slug": page.slug}
            )
    return refs


def _scan(value, url: str, stem: str) -> bool:
    if isinstance(value, str):
        return _asset_used(value, url, stem)
    if isinstance(value, dict):
        return any(_scan(v, url, stem) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_scan(v, url, stem) for v in value)
    return False


@bp.post("/images")
@jwt_required()
def upload_image():
    # Any authenticated user may add images (needed for page editing);
    # deletion stays gated behind the files permission.
    file = request.files.get("file")
    if file is None:
        return jsonify({"message": "No file provided"}), 400

    original = _safe_name(file.filename)
    ext = (os.path.splitext(original)[1] or "").lower()
    if ext not in IMAGE_EXTENSIONS:
        return jsonify({"message": "Only images (png, jpg, webp, gif) may be uploaded."}), 415
    if (file.mimetype or "") not in _IMAGE_TYPES and file.mimetype:
        return jsonify({"message": "File content is not a supported image type."}), 415

    upload_dir = current_upload_dir()
    stored = f"{uuid.uuid4().hex}_{original}"
    dest = os.path.join(upload_dir, stored)
    file.save(dest)
    size = os.path.getsize(dest)
    if size > UPLOAD_MAX_BYTES:
        _clear_file(upload_dir, stored)
        return jsonify({"message": "Image exceeds the 10 MB upload limit."}), 413

    meta = generate_variants(upload_dir, stored)

    actor = Users.objects(user_id=int(get_jwt_identity())).first()
    image = Images(
        image_id=next_id(Images, "image_id"),
        image_name=original,
        file_name=stored,
        file_path=dest,
        image_type=file.content_type,
        file_size=str(size),
        image_dimensions=meta["dimensions"],
        image_width=meta["width"],
        image_height=meta["height"],
        variants=meta["variants"],
        image_format=(os.path.splitext(original)[1] or "").lstrip("."),
        file_type=file.content_type,
        image_url=f"/uploads/{stored}",
        creator_id=actor.user_id if actor else None,
    )
    image.bump_version()
    image.save()
    log_audit("CREATE", "images", {}, {"image_id": image.image_id, "url": image.image_url})
    return jsonify(document_to_dict(image)), 201


@bp.post("/files")
@jwt_required()
def upload_file():
    # Any authenticated user may add documents (needed for page editing);
    # deletion stays gated behind the files permission.
    file = request.files.get("file")
    if file is None:
        return jsonify({"message": "No file provided"}), 400

    original = _safe_name(file.filename)
    ext = (os.path.splitext(original)[1] or "").lower()
    if ext not in FILE_EXTENSIONS:
        allowed = ", ".join(sorted(e.lstrip(".") for e in FILE_EXTENSIONS))
        return jsonify({"message": f"Only documents may be uploaded: {allowed}."}), 415

    upload_dir = current_upload_dir()
    stored = f"{uuid.uuid4().hex}_{original}"
    dest = os.path.join(upload_dir, stored)
    file.save(dest)
    size = os.path.getsize(dest)
    if size > UPLOAD_MAX_BYTES:
        _clear_file(upload_dir, stored)
        return jsonify({"message": "File exceeds the 10 MB upload limit."}), 413

    actor = Users.objects(user_id=int(get_jwt_identity())).first()
    doc = Files(
        file_id=next_id(Files, "file_id"),
        actual_file_name=stored,
        file_name=original,
        file_path=dest,
        file_size=str(size),
        file_format=(os.path.splitext(original)[1] or "").lstrip("."),
        file_url=f"/uploads/{stored}",
        file_type=file.mimetype or mimetypes.guess_type(original)[0],
        creator_id=actor.user_id if actor else None,
    )
    doc.bump_version()
    doc.save()
    log_audit("CREATE", "files", {}, {"file_id": doc.file_id, "url": doc.file_url})
    return jsonify(document_to_dict(doc)), 201


@bp.delete("/images/<int:image_id>")
@jwt_required()
def delete_image(image_id: int):
    if not has_permission(PERM_FILES, CREATE_DELETE):
        return jsonify({"message": "Permission denied"}), 403
    image = Images.objects(image_id=image_id).first()
    if image is None:
        return jsonify({"message": "Image not found"}), 404

    stem = os.path.splitext(image.file_name)[0]
    refs = _page_refs(image.image_url, stem)
    if refs:
        return jsonify(
            {
                "message": f"Image is used by {len(refs)} page(s) and cannot be deleted.",
                "references": refs,
            }
        ), 409

    upload_dir = current_upload_dir()
    _clear_file(upload_dir, image.file_name, *_variant_names(image.file_name))
    old = {"image_id": image.image_id, "url": image.image_url}
    image.delete()
    log_audit("DELETE", "images", old, {})
    return jsonify({"message": "Image deleted.", "image_id": image_id}), 200


@bp.delete("/files/<int:file_id>")
@jwt_required()
def delete_file(file_id: int):
    if not has_permission(PERM_FILES, CREATE_DELETE):
        return jsonify({"message": "Permission denied"}), 403
    doc = Files.objects(file_id=file_id).first()
    if doc is None:
        return jsonify({"message": "File not found"}), 404

    stem = os.path.splitext(doc.actual_file_name)[0]
    refs = _page_refs(doc.file_url, stem)
    if refs:
        return jsonify(
            {
                "message": f"File is referenced by {len(refs)} page(s) and cannot be deleted.",
                "references": refs,
            }
        ), 409

    upload_dir = current_upload_dir()
    _clear_file(upload_dir, doc.actual_file_name)
    old = {"file_id": doc.file_id, "url": doc.file_url}
    doc.delete()
    log_audit("DELETE", "files", old, {})
    return jsonify({"message": "File deleted.", "file_id": file_id}), 200


@bp.get("/<path:filename>")
@jwt_required()
def download(filename: str):
    """Authenticated alias kept for API clients; the website uses
    the public /uploads route registered by create_app."""
    path = resolve_variant_media(
        current_upload_dir(), filename, request.args.get("size")
    )
    return send_from_directory(
        os.path.dirname(path), os.path.basename(path), as_attachment=False
    )


def current_upload_dir() -> str:
    path = current_app.config["UPLOAD_DIR"]
    os.makedirs(path, exist_ok=True)
    return path


@bp.get("/")
@bp.get("")
@jwt_required()
def list_uploads():
    images = [document_to_dict(i) for i in Images.objects().order_by("-created_datetime")]
    files = [document_to_dict(f) for f in Files.objects().order_by("-created_datetime")]
    for image in images:
        stem = os.path.splitext(image.get("file_name") or "")[0]
        image["used_by"] = _page_refs(image.get("image_url", ""), stem)
    for doc in files:
        stem = os.path.splitext(doc.get("actual_file_name") or "")[0]
        doc["used_by"] = _page_refs(doc.get("file_url", ""), stem)
    return jsonify({"Images": images, "Files": files}), 200
