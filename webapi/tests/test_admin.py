"""Admin domain endpoint tests: pages tree, settings, roles matrix, users."""

from wblester_api.models import Categories, Pages, SiteSettings, Users


def _auth(client):
    token = client.post(
        "/auth/login", json={"username": "admin_test", "password": "secret123"}
    ).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_pages_tree_groups_pages_under_categories(client):
    Categories(category_id=1, category_name="Agri", slug="agri").save()
    Pages(page_id=10, category_id=1, title="Crops", slug="crops").save()
    Pages(page_id=11, title="Standalone", slug="standalone").save()

    resp = client.get("/cpanel/jwt/pages/tree", headers=_auth(client))
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["pages"]) == 2
    assert any(n.get("type") == "category" for n in body["tree"])


def test_set_home_page(client):
    Pages(page_id=20, title="Home", slug="home").save()
    SiteSettings(
        settings_id=1, site_name="WBLESTER", site_title="WBLESTER"
    ).save()

    resp = client.post(
        "/cpanel/jwt/pages/set_home_page/20", headers=_auth(client)
    )
    assert resp.status_code == 200
    assert SiteSettings.objects.first().home_page_id == 20


def test_settings_get_masks_secrets(client):
    settings = SiteSettings(
        settings_id=1,
        site_name="WBLESTER",
        site_title="T",
        decryption_password="supersecret",
        secret_key="also-secret",
    )
    settings.save()

    resp = client.get("/cpanel/jwt/settings", headers=_auth(client))
    body = resp.get_json()
    assert "decryption_password" not in body
    assert "secret_key" not in body


def test_roles_matrix_roundtrip(client):
    headers = _auth(client)

    resp = client.put(
        "/cpanel/jwt/roles/matrix/2",
        json={
            "cells": [
                {"permission_id": 1, "access_level": 0},
                {"permission_id": 7, "access_level": 1},
            ]
        },
        headers=headers,
    )
    assert resp.status_code == 200

    matrix = client.get("/cpanel/jwt/roles/matrix", headers=headers).get_json()
    guest_row = next(r for r in matrix["matrix"] if r["role_id"] == 2)
    levels = {c["permission_id"]: c["access_level"] for c in guest_row["cells"]}
    assert levels[1] == 0
    assert levels[7] == 1
    assert levels[2] == -1  # unset grants read as -1 (no access)


def test_create_user_with_password(client):
    resp = client.post(
        "/cpanel/jwt/users",
        json={
            "username": "newbie",
            "email": "newbie@test.local",
            "password": "pass123",
            "roleId": 2,
        },
        headers=_auth(client),
    )
    assert resp.status_code == 201
    user = Users.objects(username="newbie").first()
    assert user.check_password("pass123")
    assert "password_hash" not in resp.get_json()


def test_change_own_password_requires_current(client):
    resp = client.put(
        "/cpanel/jwt/users/1/password",
        json={"current_password": "wrong", "new_password": "n3wp4ss"},
        headers=_auth(client),
    )
    assert resp.status_code == 401

    resp = client.put(
        "/cpanel/jwt/users/1/password",
        json={"current_password": "secret123", "new_password": "n3wp4ss"},
        headers=_auth(client),
    )
    assert resp.status_code == 200

    # Old password no longer works; new one does.
    old = client.post(
        "/auth/login", json={"username": "admin_test", "password": "secret123"}
    )
    assert old.status_code == 401
    new = client.post(
        "/auth/login", json={"username": "admin_test", "password": "n3wp4ss"}
    )
    assert new.status_code == 200
