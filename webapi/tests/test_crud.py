"""Generic data endpoint tests (RBAC + audit)."""

import json

from wblester_api.models import AuditTrail, Categories, Pages


def _auth(client):
    token = client.post(
        "/auth/login", json={"username": "admin_test", "password": "secret123"}
    ).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_records_paged(client):
    for i in range(5):
        Pages(
            page_id=i + 1, title=f"Page {i}", slug=f"page-{i}", visible=True
        ).save()

    resp = client.get(
        "/cpanel/jwt/data/Pages?startIndex=2&limit=2", headers=_auth(client)
    )
    assert resp.status_code == 200
    rows = resp.get_json()["Pages"]
    assert len(rows) == 2
    assert rows[0]["page_id"] == 3


def test_get_records_with_filter(client):
    Pages(page_id=1, title="Alpha", slug="alpha").save()
    Pages(page_id=2, title="Beta", slug="beta").save()

    q = json.dumps({"pages": {"slug": "beta"}})
    resp = client.get(f"/cpanel/jwt/data/Pages?q={q}", headers=_auth(client))
    rows = resp.get_json()["Pages"]
    assert len(rows) == 1
    assert rows[0]["title"] == "Beta"


def test_upsert_creates_and_bumps_version(client):
    payload = {
        "categoryId": None,
        "categoryName": "Energy",
        "slug": "energy",
        "visible": True,
        "sortOrder": 3,
    }
    resp = client.post("/cpanel/jwt/data/Categories", json=payload, headers=_auth(client))
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["category_id"] == 1
    assert body["current_version"] == 1

    trail = AuditTrail.objects(affected_table="categories").first()
    assert trail is not None
    assert trail.change_type == "CREATE"


def test_upsert_updates_existing(client):
    client.post(
        "/cpanel/jwt/data/Categories",
        json={"categoryName": "Before", "slug": "before"},
        headers=_auth(client),
    )
    payload = {"categoryId": 1, "categoryName": "After"}
    resp = client.post("/cpanel/jwt/data/Categories", json=payload, headers=_auth(client))
    assert resp.status_code == 200
    assert resp.get_json()["category_name"] == "After"
    assert resp.get_json()["current_version"] == 2


def test_delete_records(client):
    Categories(category_id=7, category_name="Doomed", slug="doomed").save()
    resp = client.delete(
        "/cpanel/jwt/data/Categories/7", headers=_auth(client)
    )
    assert resp.status_code == 200
    assert Categories.objects(category_id=7).first() is None

    trail = AuditTrail.objects(change_type="DELETE", affected_table="categories").first()
    assert trail is not None


def test_write_requires_permission(client):
    """guest role has no grants -> write denied."""
    from wblester_api.models import RolePermissions, Roles, Users

    guest = Users(
        user_id=2, username="guest_test", email="guest@test.local",
        role_id=2, active=True,
    )
    guest.set_password("secret123")
    guest.save()

    token = client.post(
        "/auth/login", json={"username": "guest_test", "password": "secret123"}
    ).get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/cpanel/jwt/data/Pages",
        json={"title": "X", "slug": "x"},
        headers=headers,
    )
    assert resp.status_code == 403

    # Read is allowed for any authenticated user.
    resp = client.get("/cpanel/jwt/data/Pages", headers=headers)
    assert resp.status_code == 200


def test_page_create_does_not_touch_pages_sharing_category(client):
    """Regression: id-field resolution must use page_id for Pages, never
    category_id, or creating a page would overwrite an unrelated page that
    happens to share the same categoryId."""
    Pages(
        page_id=101,
        category_id=1,
        title="Seeded Agriculture",
        slug="agriculture-home",
        visible=True,
    ).save()

    resp = client.post(
        "/cpanel/jwt/data/Pages",
        json={
            "categoryId": 1,
            "title": "Brand New",
            "slug": "brand-new",
            "visible": True,
            "sortOrder": 9,
            "contentJson": {"blocks": []},
        },
        headers=_auth(client),
    )
    assert resp.status_code == 201
    created = resp.get_json()
    assert created["page_id"] != 101
    assert created["slug"] == "brand-new"

    seeded = Pages.objects(page_id=101).first()
    assert seeded is not None
    assert seeded.slug == "agriculture-home"
    assert seeded.title == "Seeded Agriculture"


def test_update_page_by_id_targets_correct_record(client):
    Pages(page_id=201, category_id=1, title="A", slug="a", visible=True).save()
    Pages(page_id=202, category_id=1, title="B", slug="b", visible=True).save()

    resp = client.put(
        "/cpanel/jwt/data/Pages/202",
        json={"title": "B2"},
        headers=_auth(client),
    )
    assert resp.status_code == 200

    assert Pages.objects(page_id=201).first().title == "A"
    assert Pages.objects(page_id=202).first().title == "B2"
