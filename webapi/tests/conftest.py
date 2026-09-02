"""Pytest fixtures using an in-memory mongomock database."""

import mongomock
import pytest

from wblester_api.app import create_app
from wblester_api.config import Config
from wblester_api.models import Permissions, RolePermissions, Roles, Users


class MockClient(mongomock.MongoClient):
    """mongoengine expects a real address tuple on the client."""

    @property
    def address(self):
        return ("localhost", 27017)


class TestConfig(Config):
    TESTING = True
    JWT_SECRET_KEY = "test-jwt-secret-that-is-long-enough-32bytes"
    MAX_LOGIN_ATTEMPTS = 3
    SYNC_API_USERNAME = "test_sync"
    SYNC_API_PASSWORD = "test_sync_pass"
    MONGO_CLIENT_CLASS = MockClient


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    _seed_baseline()
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clean_db():
    """Drop every collection after each test (connection is process-wide)."""
    yield
    from mongoengine.connection import get_db

    try:
        db = get_db()
        for name in list(db.list_collection_names()):
            db.drop_collection(name)
    except Exception:  # pragma: no cover - nothing connected yet
        pass


@pytest.fixture()
def admin_headers(client):
    resp = client.post(
        "/auth/login",
        json={"username": "admin_test", "password": "secret123"},
    )
    assert resp.status_code == 200, resp.get_json()
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_baseline() -> None:
    if Roles.objects().count() == 0:
        Roles(role_id=0, role_name="superuser", description="").save()
        Roles(role_id=1, role_name="admin", description="").save()
        Roles(role_id=2, role_name="guest", description="").save()

    if Permissions.objects().count() == 0:
        for idx, name in enumerate(
            [
                "pages", "categories", "settings", "users", "roles",
                "permissions", "messages", "files", "audit_trail",
            ]
        ):
            Permissions(permission_id=idx + 1, permission_name=name).save()

    if RolePermissions.objects(role_id=1).count() == 0:
        for perm in Permissions.objects():
            RolePermissions(
                role_id=1, permission_id=perm.permission_id, access_level=2
            ).save()

    if Users.objects(username="admin_test").count() == 0:
        user = Users(
            user_id=1,
            username="admin_test",
            email="admin@test.local",
            role_id=1,
            active=True,
        )
        user.set_password("secret123")
        user.save()
