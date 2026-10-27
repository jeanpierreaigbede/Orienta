import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.cli import create_admin
from app.crypto import keys
from app.crypto.envelope import DecryptionError, decrypt_text, encrypt_text, new_key
from tests.conftest import register_and_verify

DB = os.environ["DATABASE_URL"].replace("+psycopg", "")


def test_round_trip_and_tamper_detection():
    key = new_key()
    ciphertext, nonce = encrypt_text(key, "Je suis séropositive", "messages:c1:1")
    assert decrypt_text(key, ciphertext, nonce, "messages:c1:1") == "Je suis séropositive"
    tampered = bytes([ciphertext[0] ^ 1]) + ciphertext[1:]
    with pytest.raises(DecryptionError):
        decrypt_text(key, tampered, nonce, "messages:c1:1")
    with pytest.raises(DecryptionError):  # same ciphertext moved to another row
        decrypt_text(key, ciphertext, nonce, "messages:c2:1")


def test_same_message_never_gives_same_ciphertext():
    key = new_key()
    outputs = {encrypt_text(key, "Non", "a")[0] for _ in range(1000)}
    assert len(outputs) == 1000


def test_database_holds_no_plain_text(client):
    register_and_verify(client)
    client.post("/api/v1/conversations", json={"content": "J'ai de la fièvre et je suis enceinte"})
    with psycopg.connect(DB) as conn:
        dump = " ".join(str(row) for table in ("users", "messages")
                        for row in conn.execute(f"SELECT * FROM {table}").fetchall())
    for secret in ("awa@example.com", "Awa Houngbo", "enceinte", "fièvre"):
        assert secret not in dump
    # ...while the patient still reads their history normally.
    conversations = client.get("/api/v1/conversations").json()["items"]
    detail = client.get(f"/api/v1/conversations/{conversations[0]['id']}").json()
    assert detail["messages"][0]["content"] == "J'ai de la fièvre et je suis enceinte"


def test_encryption_switch_in_env(client):
    from app.config import get_settings

    register_and_verify(client)
    settings = get_settings()
    settings.encryption_enabled = False  # ENCRYPTION_ENABLED=false in api/.env
    try:
        conv = client.post("/api/v1/conversations", json={"content": "Message en clair"}).json()["id"]
    finally:
        settings.encryption_enabled = True
    client.post(f"/api/v1/conversations/{conv}/messages", json={"content": "Message chiffré"})
    with psycopg.connect(DB) as conn:
        rows = conn.execute("SELECT encryption_mode, content_plaintext FROM messages ORDER BY sequence").fetchall()
    assert rows[0] == ("PLAINTEXT", "Message en clair")
    assert rows[2] == ("ENCRYPTED", None)
    # Mixed history (plain + encrypted) is still readable by the patient.
    texts = [m["content"] for m in client.get(f"/api/v1/conversations/{conv}").json()["messages"]]
    assert "Message en clair" in texts and "Message chiffré" in texts


def test_kek_rotation_from_the_command_line(client, monkeypatch, capsys):
    from app import cli

    register_and_verify(client)
    conv = client.post("/api/v1/conversations", json={"content": "Avant rotation"}).json()["id"]
    with pytest.raises(SystemExit):
        cli.rotate_kek()  # no KEK_V2 loaded yet

    monkeypatch.setenv("KEK_V2", "Y2xlLW1hc3RlLXZlcnNpb24tZGV1eC0xMjM0NTY3ODk=")
    keys.get_kek_provider.cache_clear()
    cli.rotate_kek()
    assert "1 DEK(s) re-wrapped" in capsys.readouterr().out
    assert client.get(f"/api/v1/conversations/{conv}").json()["messages"][0]["content"] == "Avant rotation"
    keys.get_kek_provider.cache_clear()


def test_no_key_route_in_the_web_api(client):
    create_admin("admin@example.com", "Admin", "adminpassword1")
    admin = TestClient(client.app)
    admin.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "adminpassword1"})
    assert admin.post("/api/v1/admin/keys/rotate").status_code == 404
    assert admin.get("/api/v1/demo/raw/messages").status_code == 404
