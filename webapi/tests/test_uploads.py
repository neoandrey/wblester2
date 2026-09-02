"""Upload endpoint tests."""

import io
import os

from PIL import Image


def _auth(client):
    token = client.post(
        "/auth/login", json={"username": "admin_test", "password": "secret123"}
    ).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_image_upload_creates_document(client, tmp_path, monkeypatch):
    from wblester_api.app import create_app  # noqa: F401
    from flask import current_app

    monkeypatch.setattr(
        "wblester_api.blueprints.uploads.current_upload_dir", lambda: str(tmp_path)
    )

    data = {
        "file": (io.BytesIO(b"\x89PNG fake image"), "logo.png"),
    }
    resp = client.post(
        "/cpanel/jwt/uploads/images",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["image_name"] == "logo.png"
    assert body["image_url"].startswith("/uploads/")

    from wblester_api.models import Images

    assert Images.objects().count() == 1


def test_image_upload_with_real_upload_dir(client, tmp_path):
    """Regression: uploads must work without monkeypatching the dir helper
    (current_app used to be missing from the imports)."""
    from flask import current_app

    with client.application.app_context():
        current_app.config["UPLOAD_DIR"] = str(tmp_path)

    data = {
        "file": (io.BytesIO(b"\x89PNG fake bytes"), "dot.png"),
    }
    resp = client.post(
        "/cpanel/jwt/uploads/images",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["image_url"].startswith("/uploads/")
    stored = tmp_path / body["file_name"]
    assert stored.exists()

def _png_bytes(width=1200, height=800, color=(30, 144, 255)):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def test_image_upload_builds_responsive_variants(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)

    data = {"file": (io.BytesIO(_png_bytes()), "hero.png")}
    resp = client.post(
        "/cpanel/jwt/uploads/images",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()

    assert body["image_dimensions"] == "1200x800"
    assert body["image_width"] == 1200
    assert body["image_height"] == 800
    assert set(body["variants"]) == {"lg", "md", "sm", "thumb"}

    stem = os.path.splitext(body["file_name"])[0]
    variant_ext = os.path.splitext(body["variants"]["lg"])[1].lstrip(".")
    for variant in ("lg", "md", "sm", "thumb"):
        target = tmp_path / f"{stem}.{variant}.{variant_ext}"
        assert target.exists(), variant
        assert body["variants"][variant] == f"/uploads/{target.name}"

    # Different edge lengths per variant; never upscaled above the source.
    lg_path = tmp_path / f"{stem}.lg.{variant_ext}"
    thumb_path = tmp_path / f"{stem}.thumb.{variant_ext}"
    with Image.open(lg_path) as lg, Image.open(thumb_path) as thumb:
        assert lg.size[0] == 1200  # original width kept (below the lg cap)
        assert thumb.size[0] <= 128
        assert lg.size[0] > thumb.size[0]

    # Public media honours ?size=...
    original = client.get(body["image_url"])
    lg = client.get(body["variants"]["lg"])
    assert lg.status_code == 200
    assert len(lg.data) < len(original.data)

    # Unknown size falls back to the original (legacy uploads).
    fallback = client.get(f"{body['image_url']}?size=bogus")
    assert fallback.status_code == 200
    assert fallback.data == original.data


def test_jpeg_upload_strips_exif(client, tmp_path):
    exif = Image.Exif()
    exif[0x010F] = "WBLESTER CAMERA"
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "red").save(buf, format="JPEG", exif=exif)

    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)

    data = {"file": (io.BytesIO(buf.getvalue()), "exif.jpg")}
    resp = client.post(
        "/cpanel/jwt/uploads/images",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    stored_path = tmp_path / body["file_name"]
    with Image.open(stored_path) as im:
        assert im.getexif() == {}


def test_undecodable_image_degrades_gracefully(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)

    data = {"file": (io.BytesIO(b"\x89PNG fake image"), "logo.png")}
    resp = client.post(
        "/cpanel/jwt/uploads/images",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["variants"] == {}
    assert (tmp_path / body["file_name"]).exists()

def test_upload_rejects_unsafe_image_type(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)
    data = {"file": (io.BytesIO(b"MZ fake exe"), "tool.exe")}
    resp = client.post(
        "/cpanel/jwt/uploads/images",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 415, resp.get_json()


def test_upload_rejects_text_as_image_and_limits_documents(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)
    data = {"file": (io.BytesIO(b"<script>"), "payload.svg")}
    resp = client.post(
        "/cpanel/jwt/uploads/images",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 415, resp.get_json()

    data = {"file": (io.BytesIO(b"<script>alert(1)</script>"), "page.png")}
    resp = client.post(
        "/cpanel/jwt/uploads/files",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 415, resp.get_json()


def test_doc_upload_and_dependency_aware_delete(client, tmp_path):
    from wblester_api.models import Files, Pages

    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)

    def _pdf():
        return {"file": (io.BytesIO(b"%PDF-1.4 fake"), "guide.pdf")}

    resp = client.post(
        "/cpanel/jwt/uploads/files",
        headers=_auth(client),
        data=_pdf(),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.get_json()
    doc = resp.get_json()
    fid = doc["file_id"]
    url = doc["file_url"]

    resp = client.delete(f"/cpanel/jwt/uploads/files/{fid}", headers=_auth(client))
    assert resp.status_code == 200
    assert Files.objects(file_id=fid).first() is None

    resp = client.post(
        "/cpanel/jwt/uploads/files",
        headers=_auth(client),
        data=_pdf(),
        content_type="multipart/form-data",
    )
    doc = resp.get_json()
    fid = doc["file_id"]
    url = doc["file_url"]

    Pages(
        page_id=1, category_id=1, title="Guide", slug="guide",
        content_json={"blocks": [{"type": "richText", "html": f'<a href="{url}">guide</a>'}]},
    ).save()

    resp = client.delete(f"/cpanel/jwt/uploads/files/{fid}", headers=_auth(client))
    assert resp.status_code == 409, resp.get_json()
    assert resp.get_json()["references"][0]["page_id"] == 1
    assert Files.objects(file_id=fid).first() is not None

    Pages.objects().delete()


def test_image_delete_blocks_when_referenced_via_variant(client, tmp_path):
    from wblester_api.models import Images, Pages

    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)

    data = {"file": (io.BytesIO(_png_bytes()), "hero.png")}
    resp = client.post(
        "/cpanel/jwt/uploads/images",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    body = resp.get_json()
    stem = os.path.splitext(body["file_name"])[0]
    variant_url = f"/uploads/{stem}.md.jpg"
    Pages(
        page_id=2, category_id=1, title="Home", slug="home",
        content_json={"blocks": [{"type": "hero", "imageUrl": variant_url}]},
    ).save()

    resp = client.delete(
        f"/cpanel/jwt/uploads/images/{body['image_id']}", headers=_auth(client)
    )
    assert resp.status_code == 409, resp.get_json()
    assert resp.get_json()["references"][0]["page_id"] == 2
    assert Images.objects(image_id=body["image_id"]).first() is not None

    Pages.objects().delete()
    resp = client.delete(
        f"/cpanel/jwt/uploads/images/{body['image_id']}", headers=_auth(client)
    )
    assert resp.status_code == 200
    assert Images.objects(image_id=body["image_id"]).first() is None


def test_list_uploads_reports_usage(client, tmp_path):
    from wblester_api.models import Pages

    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)

    data = {"file": (io.BytesIO(_png_bytes(width=64, height=64)), "tiny.png")}
    resp = client.post(
        "/cpanel/jwt/uploads/images",
        headers=_auth(client),
        data=data,
        content_type="multipart/form-data",
    )
    body = resp.get_json()
    Pages(
        page_id=3,
        title="Tiny",
        slug="tiny",
        content_json={"blocks": [{"type": "gallery", "items": [{"imageUrl": body["image_url"]}]}]},
    ).save()

    listing = client.get("/cpanel/jwt/uploads", headers=_auth(client)).get_json()
    assert any(i["used_by"] and i["used_by"][0]["page_id"] == 3 for i in listing["Images"])
    Pages.objects().delete()
