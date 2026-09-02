"""Sync contract tests: delta pull and update fetch."""

from wblester_api.models import Categories


def _auth(client):
    token = client.post(
        "/auth/login", json={"username": "admin_test", "password": "secret123"}
    ).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_sync_pull_returns_table_payload(client):
    Categories(
        category_id=1, parent_id=None, category_name="Agriculture",
        slug="agriculture", visible=True, sort_order=1,
    ).save()

    resp = client.get("/cpanel/jwt/sync/cpanel/Categories", headers=_auth(client))
    assert resp.status_code == 200
    body = resp.get_json()
    assert "Categories" in body
    record = body["Categories"][0]
    # snake_case keys per the sync contract
    assert record["category_id"] == 1
    assert record["category_name"] == "Agriculture"
    assert record["current_version"] == 0
    assert "last_modified_date" in record


def test_sync_delta_by_version(client):
    Categories(category_id=1, category_name="Old", slug="old").save()
    new = Categories(category_id=2, category_name="New", slug="new")
    new.bump_version()  # version 1
    new.save()

    headers = _auth(client)
    all_rows = client.get(
        "/cpanel/jwt/sync/cpanel/Categories", headers=headers
    ).get_json()["Categories"]
    assert len(all_rows) == 2

    deltas = client.get(
        "/cpanel/jwt/sync/cpanel/Categories?since_version=0", headers=headers
    ).get_json()["Categories"]
    assert len(deltas) == 1
    assert deltas[0]["category_id"] == 2


def test_update_fetch_by_ids(client):
    Categories(category_id=5, category_name="Five", slug="five").save()
    Categories(category_id=6, category_name="Six", slug="six").save()

    import json

    resp = client.get(
        "/cpanel/jwt/sync/update/cpanel?q=" + json.dumps({"Categories": [5]}),
        headers=_auth(client),
    )
    assert resp.status_code == 200
    rows = resp.get_json()["Categories"]
    assert len(rows) == 1
    assert rows[0]["category_id"] == 5


def test_sync_requires_jwt(client):
    resp = client.get("/cpanel/jwt/sync/cpanel/Categories")
    assert resp.status_code == 401


def test_unknown_table_404(client):
    resp = client.get("/cpanel/jwt/sync/cpanel/Nope", headers=_auth(client))
    assert resp.status_code == 404
