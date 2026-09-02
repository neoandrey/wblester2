"""Session-14 features: notification mails, forced password change,
dashboard stats and the consolidated SIEM-style log stream."""

from wblester_api.models import Roles, Users


def _auth(client):
    token = client.post(
        "/auth/login", json={"username": "admin_test", "password": "secret123"}
    ).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _superuser(client):
    """Login as a fresh superuser (role 0) for superuser-only endpoints."""
    Roles(role_id=0, role_name="superuser", description="").save()
    u = Users(
        user_id=99,
        username="root_test",
        email="root@test.local",
        role_id=0,
        active=True,
    )
    u.set_password("rootsecret")
    u.save()
    token = client.post(
        "/auth/login", json={"username": "root_test", "password": "rootsecret"}
    ).get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_user_notifies_and_arms_change(client, monkeypatch):
    sent = {}
    monkeypatch.setattr(
        "wblester_api.blueprints.users.send_mail",
        lambda recipients, subject, html: sent.update(
            recipients=list(recipients), subject=subject, html=html
        ),
    )

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
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["must_change_password"] is True
    assert sent["recipients"] == ["newbie@test.local"]
    assert "created" in sent["subject"].lower()
    assert "pass123" not in sent["html"]  # never leak the initial password

    user = Users.objects(username="newbie").first()
    assert user.must_change_password is True


def test_change_own_password_clears_flag(client):
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
    user_id = resp.get_json()["user_id"]

    login = client.post(
        "/auth/login", json={"username": "newbie", "password": "pass123"}
    )
    assert login.status_code == 200
    headers = {
        "Authorization": "Bearer " + login.get_json()["access_token"]
    }

    resp = client.put(
        f"/cpanel/jwt/users/{user_id}/password",
        json={"current_password": "pass123", "new_password": "n3wp4ss"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert Users.objects(user_id=user_id).first().must_change_password is False


def test_admin_reset_arms_change(client):
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
    user_id = resp.get_json()["user_id"]

    # The user changed their own password already -> flag cleared.
    login = client.post(
        "/auth/login", json={"username": "newbie", "password": "pass123"}
    ).get_json()["access_token"]
    client.put(
        f"/cpanel/jwt/users/{user_id}/password",
        json={"current_password": "pass123", "new_password": "other44"},
        headers={"Authorization": f"Bearer {login}"},
    )
    Users.objects(user_id=user_id).first().reload()
    assert Users.objects(user_id=user_id).first().must_change_password is False

    # Admins resetting the password re-arm the forced change.
    resp = client.put(
        f"/cpanel/jwt/users/{user_id}/password",
        json={"new_password": "adminreset"},
        headers=_auth(client),
    )
    assert resp.status_code == 200
    assert Users.objects(user_id=user_id).first().must_change_password is True


def test_stats_endpoint(client):
    from wblester_api.models import Images

    Images(
        image_id=5, image_name="a.png", file_name="a.png",
        file_path="/u/a.png", image_url="/a.png", file_size="1024",
        variants={"lg": "/a.png?size=lg"},
    ).save()

    resp = client.get("/cpanel/jwt/stats", headers=_auth(client))
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["frontend"]["images"] == 1
    assert body["frontend"]["storage_bytes"] == 1024
    assert body["frontend"]["image_variants"] == 1
    assert body["webapi"]["users"] >= 1
    assert body["backend"]["pages"] == 0


def test_stats_requires_auth(client):
    resp = client.get("/cpanel/jwt/stats")
    assert resp.status_code == 401


def test_frontend_log_ingest_and_superuser_view(client):
    headers = _auth(client)
    bad = client.post(
        "/cpanel/jwt/logs/frontend", json={}, headers=headers
    )
    assert bad.status_code == 400

    resp = client.post(
        "/cpanel/jwt/logs/frontend",
        json={"level": "ERROR", "page": "images", "message": "upload failed"},
        headers=headers,
    )
    assert resp.status_code == 201

    # Admins can ingest but not read the consolidated stream.
    denied = client.get("/cpanel/jwt/logs", headers=headers)
    assert denied.status_code == 403

    root = _superuser(client)
    ok = client.get("/cpanel/jwt/logs", headers=root)
    assert ok.status_code == 200
    body = ok.get_json()
    rows = body["logs"]
    assert any(
        r["source"] == "frontend"
        and r["level"] == "ERROR"
        and "upload failed" in r["message"]
        for r in rows
    )

    filtered = client.get(
        "/cpanel/jwt/logs?source=frontend&level=ERROR", headers=root
    ).get_json()
    assert filtered["logs"] and all(
        r["source"] == "frontend" and r["level"] == "ERROR"
        for r in filtered["logs"]
    )