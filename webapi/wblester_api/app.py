"""Flask application factory."""

import os
from pathlib import Path

import mongoengine
from flask import Flask, jsonify, redirect, request, send_from_directory
from werkzeug.exceptions import NotFound

from .config import Config
from .extensions import cors, jwt
from .logging_setup import configure_logging
from .login_page import LOGIN_PAGE
from .logs_page import LOGS_PAGE


def _wants_html() -> bool:
    """True when the caller looks like a browser navigation."""
    accept = request.headers.get("Accept", "")
    return "text/html" in accept and "application/json" not in accept.split(",")[
        0
    ]


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_object is not None:
        app.config.from_object(config_object)

    configure_logging()
    _load_dotenv()
    _init_mongo(app)

    cors.origins = "*"
    cors.init_app(
        app,
        resources={r"/*": {"origins": "*", "supports_credentials": False}},
    )
    jwt.init_app(app)

    from .blueprints import ALL_BLUEPRINTS

    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/uploads/<path:filename>")
    def public_media(filename: str):
        """Public media serving — the website renders images without tokens.
        Supports ``?size=lg|md|sm|thumb`` to pick a generated variant."""
        from .blueprints.uploads import current_upload_dir
        from .utils.images import resolve_variant_media

        path = resolve_variant_media(
            current_upload_dir(), filename, request.args.get("size")
        )
        return send_from_directory(os.path.dirname(path), os.path.basename(path), as_attachment=False)

    @app.get("/login")
    def login_page():
        return LOGIN_PAGE

    @app.get("/logs")
    def logs_page():
        """System status console (data endpoint enforces superuser JWT)."""
        return LOGS_PAGE

    @app.get("/admin")
    @app.get("/admin/")
    @app.get("/admin/<path:_rest>")
    def admin_spa(_rest: str = ""):
        """Admin portal entry point.

        Serves the compiled Flutter admin bundle (backend/build/web) for every
        /admin path — real bundle assets first, then index.html for deep links
        so the client router owns navigation. During the migration, when no
        Flutter build exists yet, it falls back to the frontend bundle where
        the legacy JS admin panel lives.
        """
        admin = _admin_spa_dir()
        if admin is not None:
            if _rest:
                try:
                    return send_from_directory(admin, _rest)
                except NotFound:
                    pass
            return send_from_directory(admin, "index.html")
        spa = _spa_dir()
        if spa is None:
            return redirect("/login")
        return send_from_directory(spa, "index.html")

    def _spa_dir():
        root = app.config.get("SPA_DIR") or os.environ.get("SPA_DIR")
        if not root:
            return None
        path = Path(root)
        return path if (path / "index.html").exists() else None

    def _admin_spa_dir():
        root = app.config.get("ADMIN_SPA_DIR") or os.environ.get("ADMIN_SPA_DIR")
        if not root:
            return None
        path = Path(root)
        return path if (path / "index.html").exists() else None

    @app.get("/")
    def root():
        # The public website is served straight from the API: browsers get
        # the compiled Flutter web app, machine clients keep a JSON index.
        spa = _spa_dir()
        if _wants_html() and spa is not None:
            return send_from_directory(spa, "index.html")
        if _wants_html():
            return redirect("/login")
        return jsonify(
            service="WBLESTER & O API",
            status="ok",
            health="/health",
            login="/login",
        )

    @app.get("/<path:filename>")
    def spa_files(filename: str):
        """Serve the SPA bundle and let the client router own deep links."""
        spa = _spa_dir()
        if spa is not None:
            try:
                return send_from_directory(spa, filename)
            except NotFound:
                pass
            if _wants_html():
                return send_from_directory(spa, "index.html")
        return jsonify({"message": "Not found"}), 404

    @app.errorhandler(404)
    def not_found(_error):
        spa = _spa_dir()
        if _wants_html() and spa is not None:
            return send_from_directory(spa, "index.html")
        if _wants_html():
            return redirect("/login")
        return jsonify({"message": "Not found"}), 404

    @jwt.unauthorized_loader
    def unauthorized(_reason):
        if _wants_html():
            return redirect("/login")
        return jsonify({"message": "Missing Authorization Header"}), 401

    return app


def _load_dotenv() -> None:
    """Load a local .env file when present (dev convenience)."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # pragma: no cover - dotenv optional
        pass


def _init_mongo(app: Flask) -> None:
    """Connect using discrete settings so credentials never need URI escaping."""
    username = (
        app.config.get("MONGODB_USERNAME")
        or os.environ.get("MONGODB_USERNAME")
    )
    password = (
        app.config.get("MONGODB_PASSWORD")
        or os.environ.get("MONGODB_PASSWORD")
    )
    kwargs = {}
    client_class = app.config.get("MONGO_CLIENT_CLASS")
    if client_class is not None:
        kwargs["mongo_client_class"] = client_class
    kwargs["uuidRepresentation"] = "standard"
    if username and password:
        kwargs["username"] = username
        kwargs["password"] = password
        kwargs["authentication_source"] = os.environ.get(
            "MONGODB_AUTH_SOURCE", "admin"
        )
    mongo_url =  app.config.get("MONGO_URL") or os.environ.get("MONGO_URL")
    if mongo_url:
        mongoengine.connect(
        host=mongo_url,
        retryWrites=True,
        maxIdleTimeMS=60000,
        socketTimeoutMS=20000,
        connectTimeoutMS=20000,)
        return
    mongoengine.connect(
        host=(
            app.config.get("MONGODB_HOST")
            or os.environ.get("MONGODB_HOST", "localhost")
        ),
        port=int(
            app.config.get("MONGODB_PORT")
            or os.environ.get("MONGODB_PORT", "27017")
        ),
        db=app.config["MONGODB_DB"],
        **kwargs,
    )
