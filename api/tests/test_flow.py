from fastapi.testclient import TestClient

from app.cli import create_admin
from tests.conftest import SENT_MAILS, last_code, register_and_verify


def test_register_verify_and_role(client):
    register_and_verify(client)
    me = client.get("/api/v1/auth/me").json()
    assert me["role"] == "PATIENT" and me["status"] == "ACTIVE" and me["fullName"] == "Awa Houngbo"


def test_login_before_verification_is_refused(client):
    client.post("/api/v1/auth/register", json={"email": "kofi@example.com", "password": "motdepasse123",
                                               "fullName": "Kofi Mensah", "consentVersion": "2026-10"})
    r = client.post("/api/v1/auth/login", json={"email": "kofi@example.com", "password": "motdepasse123"})
    assert r.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


def test_wrong_code_counts_attempts(client):
    client.post("/api/v1/auth/register", json={"email": "s@example.com", "password": "motdepasse123",
                                               "fullName": "Sena", "consentVersion": "2026-10"})
    r = client.post("/api/v1/auth/verify-email", json={"email": "s@example.com", "code": "000000" if last_code("s@example.com") != "000000" else "111111"})
    assert r.status_code == 422 and r.json()["error"]["details"]["attemptsLeft"] == 4


def test_duplicate_registration_does_not_leak(client):
    register_and_verify(client)
    r = client.post("/api/v1/auth/register", json={"email": "awa@example.com", "password": "autremotdepasse",
                                                   "fullName": "Xavier", "consentVersion": "2026-10"})
    assert r.status_code == 202
    assert SENT_MAILS[-1]["template"] == "already_registered"


def test_patient_cannot_open_agent_space(client):
    register_and_verify(client)
    assert client.get("/api/v1/agent/callbacks").json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_full_emergency_flow(client):
    register_and_verify(client)
    r = client.post("/api/v1/conversations", json={"content": "J'ai de la fièvre depuis hier"})
    assert r.status_code == 201, r.text
    conv = r.json()
    assert conv["status"] == "IN_PROGRESS" and len(conv["messages"]) == 2
    r = client.post(f"/api/v1/conversations/{conv['id']}/messages", json={"content": "J'ai du mal à respirer"})
    assert r.json()["orientationLevel"] == "EMERGENCY" and r.json()["status"] == "ORIENTED"
    r = client.post(f"/api/v1/conversations/{conv['id']}/messages", json={"content": "encore"})
    assert r.json()["error"]["code"] == "CONVERSATION_CLOSED"

    # Admin invites an agent, the agent accepts and handles the callback.
    create_admin("admin@example.com", "Admin", "adminpassword1")
    admin = TestClient(client.app)
    assert admin.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "adminpassword1"}).status_code == 200
    r = admin.post("/api/v1/admin/users", json={"email": "agent@example.com", "fullName": "Agent Dossou", "role": "HEALTH_AGENT"})
    assert r.status_code == 201, r.text

    agent = TestClient(client.app)
    r = agent.post("/api/v1/auth/accept-invitation", json={"email": "agent@example.com", "code": last_code("agent@example.com"),
                                                          "password": "agentpassword1"})
    assert r.json()["user"]["role"] == "HEALTH_AGENT"
    callbacks = agent.get("/api/v1/agent/callbacks").json()
    assert len(callbacks) == 1 and callbacks[0]["patientName"] == "Awa Houngbo"
    cb = callbacks[0]["id"]
    assert agent.get(f"/api/v1/agent/callbacks/{cb}/conversation").status_code == 404  # not assigned yet
    assert agent.post(f"/api/v1/agent/callbacks/{cb}/assign").json()["status"] == "ASSIGNED"
    assert agent.post(f"/api/v1/agent/callbacks/{cb}/assign").json()["error"]["code"] == "CALLBACK_ALREADY_ASSIGNED"
    assert len(agent.get(f"/api/v1/agent/callbacks/{cb}/conversation").json()["messages"]) == 4
    r = agent.post(f"/api/v1/agent/callbacks/{cb}/close", json={"outcome": "COMPLETED", "note": "Patiente orientée vers le CHU"})
    assert r.json()["status"] == "COMPLETED"

    actions = [a["action"] for a in admin.get("/api/v1/admin/audit-logs").json()]
    assert "conversation.read" in actions and "callback.closed" in actions


def test_refresh_rotation_and_reuse_detection(client):
    register_and_verify(client)
    old = client.cookies.get("refresh_token")
    assert client.post("/api/v1/auth/refresh").status_code == 200
    reuse = TestClient(client.app)
    reuse.cookies.set("refresh_token", old, path="/api/v1/auth")
    assert reuse.post("/api/v1/auth/refresh").status_code == 401
    # The whole family is revoked, including the latest token.
    assert client.post("/api/v1/auth/refresh").status_code == 401
