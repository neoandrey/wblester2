"""Application configuration loaded from environment variables."""

import os


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")

    JWT_ACCESS_TOKEN_EXPIRES = _int_env("JWT_ACCESS_TOKEN_EXPIRES", 3600)
    JWT_REFRESH_TOKEN_EXPIRES = _int_env("JWT_REFRESH_TOKEN_EXPIRES", 604800)

    MONGODB_HOST = os.environ.get("MONGODB_HOST", "localhost")
    MONGODB_PORT = _int_env("MONGODB_PORT", 27017)
    MONGODB_DB = os.environ.get("MONGODB_DB", "wblester")
    MONGODB_USERNAME = os.environ.get("MONGODB_USERNAME")
    MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD")

    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = _int_env("REDIS_PORT", 6379)
    REDIS_USERNAME = os.environ.get("REDIS_USERNAME",None)
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD",None)

    UPLOAD_DIR = os.environ.get(
        "UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "uploads")
    )
    MAX_CONTENT_LENGTH = _int_env("MAX_UPLOAD_BYTES", 32 * 1024 * 1024)

    # Absolute base used when seeding content that references uploads, so
    # the public website can resolve media without knowing the host.
    PUBLIC_BASE_URL = os.environ.get(
        "PUBLIC_BASE_URL", f"http://localhost:{os.environ.get('PORT', '5454')}"
    )

    # Compiled frontend SPA served at / for browsers. Empty disables the
    # static hosting for the public site (JSON-only API mode stays on).
    SPA_DIR = os.environ.get("SPA_DIR", "")

    # Compiled Flutter admin portal (backend/build/web) served at /admin*.
    # When empty or missing a build, /admin* falls back to SPA_DIR so a
    # legacy admin keeps working during the Flutter migration.
    ADMIN_SPA_DIR = os.environ.get("ADMIN_SPA_DIR", "")

    # Rotating application log consumed by /cpanel/jwt/diagnostics.
    LOG_DIR = os.environ.get("LOG_DIR", "")

    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = _int_env("SMTP_PORT", 587)
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "no-reply@wblester.local"
    )

    # Public URL of the admin panel, embedded in user-created notification
    # mails and the default target behind auth redirects.
    PANEL_URL = os.environ.get("PANEL_URL", "/admin")

    # Login lockout policy (mirrors the Users drift table columns).
    MAX_LOGIN_ATTEMPTS = _int_env("MAX_LOGIN_ATTEMPTS", 3)

    SYNC_API_USERNAME = os.environ.get("WBLESTER_API_USERNAME", "wblester_sync")
    SYNC_API_PASSWORD = os.environ.get("WBLESTER_API_PASSWORD", "WBLester@123")

    # Injectable pymongo-compatible client class (tests use mongomock).
    MONGO_CLIENT_CLASS = None
