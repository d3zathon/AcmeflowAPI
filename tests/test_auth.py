from .conftest import auth_headers


def test_login_success(client):
    resp = client.post("/api/v1/auth/login", data={"username": "alice", "password": "Alice#2024"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client):
    resp = client.post("/api/v1/auth/login", data={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/api/v1/auth/login", data={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_me_rejects_garbage_token(client):
    resp = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_me_returns_correct_identity(client):
    headers = auth_headers(client, "alice")
    resp = client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"
    assert resp.json()["role"] == "Employee"
