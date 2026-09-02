"""Auth endpoint tests."""


def test_login_success(client):
    resp = client.post(
        "/auth/login",
        json={"username": "admin_test", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["username"] == "admin_test"
    assert "password_hash" not in body["user"]
    assert body["user"]["role_name"] == "admin"
    # admin role holds grants for every permission in the baseline matrix
    assert set(body["user"]["permissions"]) >= {"pages", "categories", "users"}


def test_superuser_payload_lists_all_permissions(client):
    from wblester_api.models import Roles, Users

    if not Roles.objects(role_name="superuser").first():
        Roles(role_id=0, role_name="superuser").save()
    root = Users(
        user_id=99,
        username="root_test",
        email="root@test.local",
        role_id=0,
        active=True,
    )
    root.set_password("rootpass123")
    root.save()

    resp = client.post(
        "/auth/login",
        json={"username": "root_test", "password": "rootpass123"},
    )
    assert resp.status_code == 200, resp.get_json()
    perms = resp.get_json()["user"]["permissions"]
    assert isinstance(perms, list) and len(perms) >= 9
    assert "files" in perms


def test_login_wrong_password_increments_attempts(client):
    for _ in range(2):
        resp = client.post(
            "/auth/login",
            json={"username": "admin_test", "password": "wrong"},
        )
        assert resp.status_code == 401

    from wblester_api.models import Users

    user = Users.objects(username="admin_test").first()
    assert user.login_attempts == 2
    assert not user.locked


def test_login_lockout_after_max_attempts(client):
    for _ in range(3):
        client.post(
            "/auth/login", json={"username": "admin_test", "password": "wrong"}
        )

    resp = client.post(
        "/auth/login", json={"username": "admin_test", "password": "secret123"}
    )
    assert resp.status_code == 401
    assert resp.get_json()["message"] == "Account locked"


def test_refresh_flow(client):
    login = client.post(
        "/auth/login",
        json={"username": "admin_test", "password": "secret123"},
    ).get_json()

    resp = client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {login['refresh_token']}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["access_token"]


def test_m2m_credentials(client):
    resp = client.post(
        "/auth/login",
        json={"username": "test_sync", "password": "test_sync_pass"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["access_token"]
