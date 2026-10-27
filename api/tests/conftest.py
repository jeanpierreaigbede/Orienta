import os

# Tests run against a dedicated database (created by the README instructions: orienta_test).
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://orienta:orienta@localhost:5432/orienta_test")
os.environ["LLM_PROVIDER"] = "fake"
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-0123")
os.environ.setdefault("CODE_HMAC_KEY", "test-code-key")
os.environ["KEK_V1"] = "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="  # test-only key
os.environ["BLIND_INDEX_KEY"] = "YmxpbmQtaW5kZXgta2V5LWZvci10ZXN0cy0xMjM0NTY="
os.environ["ENCRYPTION_ENABLED"] = "true"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402

SENT_MAILS: list[dict] = []


@pytest.fixture(scope="session", autouse=True)
def database():
    config = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    config.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    # Start from an empty schema: the test database is shared by both chatbot branches.
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    with engine.begin() as conn:
        tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT IN ('alembic_version', 'key_encryption_keys')")).scalars().all()
        if tables:
            conn.execute(text("TRUNCATE " + ", ".join(tables) + " CASCADE"))
        # Keep the KEK version 1 row created by migration 0002, and undo any rotation from a previous test.
        conn.execute(text("DELETE FROM key_encryption_keys WHERE version > 1"))
        conn.execute(text("UPDATE key_encryption_keys SET status = 'ACTIVE', retired_at = NULL WHERE version = 1"))
    SENT_MAILS.clear()

    def fake_send(to, template, **params):
        SENT_MAILS.append({"to": to, "template": template, **params})

    monkeypatch.setattr("app.modules.auth.service.send_template", fake_send)
    monkeypatch.setattr("app.modules.auth.router.send_template", fake_send)
    yield


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def last_code(email: str) -> str:
    return [m for m in SENT_MAILS if m["to"] == email][-1]["code"]


def register_and_verify(client: TestClient, email: str = "awa@example.com") -> TestClient:
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "motdepasse123", "fullName": "Awa Houngbo",
        "phone": "+229 01 97 12 34 56", "consentVersion": "2026-10",
    })
    assert r.status_code == 202, r.text
    r = client.post("/api/v1/auth/verify-email", json={"email": email, "code": last_code(email)})
    assert r.status_code == 200, r.text
    return client
