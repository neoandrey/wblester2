"""Diagnostics endpoint + /logs page tests."""


def _login(client, username, password):
    return client.post(
        "/auth/login", json={"username": username, "password": password}
    )


def _make_superuser(app):
    from wblester_api.models import Roles, Users

    if not Roles.objects(role_name="superuser").first():
        Roles(role_id=0, role_name="superuser", description="").save()
    if not Users.objects(username="root_diag").first():
        user = Users(
            user_id=98,
            username="root_diag",
            email="rootdiag@test.local",
            role_id=0,
            active=True,
        )
        user.set_password("rootpass123")
        user.save()


def test_logs_page_is_public_html(client):
    resp = client.get("/logs", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert b"System status" in resp.data


def test_diagnostics_requires_token(client):
    resp = client.get("/cpanel/jwt/diagnostics")
    assert resp.status_code == 401


def test_diagnostics_rejects_non_superuser(client, admin_headers):
    resp = client.get("/cpanel/jwt/diagnostics", headers=admin_headers)
    assert resp.status_code == 403
    assert resp.get_json()["message"] == "Superuser role required"


def test_diagnostics_payload_for_superuser(client):
    _make_superuser(None)
    resp = _login(client, "root_diag", "rootpass123")
    assert resp.status_code == 200
    token = resp.get_json()["access_token"]

    resp = client.get(
        "/cpanel/jwt/diagnostics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()

    assert body["overall"] in {"up", "degraded", "attention"}
    names = {s["name"] for s in body["services"]}
    assert {"API", "MongoDB"} <= names

    # Redis may be absent in the test environment: it must degrade gracefully.
    redis = next(s for s in body["services"] if s["name"] == "Redis")
    assert redis["status"] in {"up", "down", "not-configured"}

    assert set(body["counts"]) >= {"error", "warning"}
    assert isinstance(body["logs"], list)
    for row in body["logs"]:
        assert set(row) >= {"ts", "level", "logger", "message"}


def test_diagnostics_logs_are_appended_and_read_back(client):
    import logging

    from wblester_api.logging_setup import configure_logging, read_recent_logs

    configure_logging()
    logging.getLogger("test.probe").warning("diagnostic probe entry")

    rows = read_recent_logs(limit=50)
    assert any(
        r["level"] == "WARNING" and "diagnostic probe entry" in r["message"]
        for r in rows
    )

    _make_superuser(None)
    token = _login(client, "root_diag", "rootpass123").get_json()[
        "access_token"
    ]
    resp = client.get(
        "/cpanel/jwt/diagnostics",
        headers={"Authorization": f"Bearer {token}"},
    )
    counts = resp.get_json()["counts"]
    assert counts["warning"] >= 1
