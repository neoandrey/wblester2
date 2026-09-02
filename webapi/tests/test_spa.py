"""Root route + SPA hosting behaviour."""


def test_root_json_index_for_api_clients(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["service"] == "WBLESTER & O API"
    assert body["status"] == "ok"


def test_unknown_path_returns_json_for_api_clients(client):
    resp = client.get("/definitely/not/here")
    assert resp.status_code == 404
    assert resp.get_json()["message"] == "Not found"


def _make_spa(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "index.html").write_text("<html>SPA HOME</html>")
    (tmp_path / "main.dart.js").write_text("// bundle")
    sub = tmp_path / "assets"
    sub.mkdir(exist_ok=True)
    (sub / "logo.svg").write_text("<svg/>")
    return tmp_path


def _make_admin_build(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "index.html").write_text("<html>ADMIN FLUTTER</html>")
    (tmp_path / "main.dart.js").write_text("// admin bundle")
    assets = tmp_path / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "NavBar_icon.png").write_text("png")
    return tmp_path


def test_spa_serving_rules(client, tmp_path):
    spa = _make_spa(tmp_path)
    app = client.application
    app.config["SPA_DIR"] = str(spa)
    tc = app.test_client()

    # Browsers get the compiled app at the root.
    resp = tc.get("/", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert b"SPA HOME" in resp.data

    # Deep links fall back to index.html for browsers.
    resp = tc.get("/page/agriculture-home", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert b"SPA HOME" in resp.data

    # Real bundle files are served (including nested asset paths).
    resp = tc.get("/main.dart.js")
    assert resp.status_code == 200
    assert b"// bundle" in resp.data
    resp = tc.get("/assets/logo.svg")
    assert resp.status_code == 200

    # Missing assets for non-browser clients stay JSON errors.
    resp = tc.get("/missing.js")
    assert resp.status_code == 404
    assert resp.get_json()["message"] == "Not found"

    # API clients on / still receive the JSON index.
    body = tc.get("/").get_json()
    assert body["service"] == "WBLESTER & O API"

    app.config["SPA_DIR"] = ""


def test_admin_served_from_admin_spa_dir(client, tmp_path):
    admin = _make_admin_build(tmp_path / "admin_build")
    app = client.application
    app.config["ADMIN_SPA_DIR"] = str(admin)
    app.config["SPA_DIR"] = ""
    tc = app.test_client()
    try:
        # /admin entry serves the Flutter shell.
        resp = tc.get("/admin")
        assert resp.status_code == 200
        assert b"ADMIN FLUTTER" in resp.data

        # Deep links return the Flutter shell for the client router.
        resp = tc.get("/admin/pages/edit/101", headers={"Accept": "text/html"})
        assert resp.status_code == 200
        assert b"ADMIN FLUTTER" in resp.data

        # Real bundle assets (main dart + nested assets) are served.
        resp = tc.get("/admin/main.dart.js")
        assert resp.status_code == 200
        assert b"// admin bundle" in resp.data
        resp = tc.get("/admin/assets/NavBar_icon.png")
        assert resp.status_code == 200
        assert resp.data == b"png"

        # The public site is unaffected (no SPA configured -> JSON root).
        resp = tc.get("/")
        assert resp.status_code == 200
        assert resp.get_json()["service"] == "WBLESTER & O API"
    finally:
        app.config["ADMIN_SPA_DIR"] = ""
        app.config["SPA_DIR"] = ""


def test_admin_falls_back_to_spa_dir_without_admin_build(client, tmp_path):
    spa = _make_spa(tmp_path / "frontend")
    app = client.application
    app.config["ADMIN_SPA_DIR"] = str(tmp_path / "no_build")
    app.config["SPA_DIR"] = str(spa)
    tc = app.test_client()
    try:
        # No Flutter build -> legacy JS admin keeps serving from the SPA.
        resp = tc.get("/admin", headers={"Accept": "text/html"})
        assert resp.status_code == 200
        assert b"SPA HOME" in resp.data
    finally:
        app.config["ADMIN_SPA_DIR"] = ""
        app.config["SPA_DIR"] = ""


def test_admin_redirects_to_login_without_any_spa(client):
    app = client.application
    app.config["ADMIN_SPA_DIR"] = ""
    app.config["SPA_DIR"] = ""
    tc = app.test_client()
    resp = tc.get("/admin")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_spa_traversal_is_blocked(client, tmp_path):
    secret = tmp_path.parent / "spa_secret.txt"
    secret.write_text("top secret")
    spa = tmp_path / "web"
    spa.mkdir(exist_ok=True)
    (spa / "index.html").write_text("<html>ok</html>")

    app = client.application
    app.config["SPA_DIR"] = str(spa)
    try:
        for candidate in (
            "/..%2f..%2fspa_secret.txt",
            "/%2e%2e/spa_secret.txt",
            "/../../../spa_secret.txt",
        ):
            resp = client.get(candidate)
            assert resp.status_code == 404
            if resp.mimetype == "application/json":
                assert resp.get_json()["message"] == "Not found"
    finally:
        app.config["SPA_DIR"] = ""
