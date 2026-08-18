from .conftest import auth_headers


def test_vuln_mass_assignment_privilege_escalation(client):
    """VULN-3: PATCH /api/v1/users/me accepts and applies a `role` field."""
    headers = auth_headers(client, "alice")

    pre = client.get("/api/v1/users/me", headers=headers)
    assert pre.json()["role"] == "Employee"

    resp = client.patch("/api/v1/users/me", headers=headers, json={"role": "Admin"})
    assert resp.status_code == 200  # <- should reject unknown/forbidden fields
    assert resp.json()["role"] == "Admin"

    # Escalation persists and is now usable via admin-only endpoints.
    post = client.get("/api/v1/users/me", headers=headers)
    assert post.json()["role"] == "Admin"

    admin_check = client.get("/api/v1/admin/users", headers=headers)
    assert admin_check.status_code == 200  # alice is now treated as Admin


def test_vuln_mass_assignment_can_also_toggle_is_active(client):
    headers = auth_headers(client, "carol")
    resp = client.patch("/api/v1/users/me", headers=headers, json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_legitimate_profile_fields_still_work(client):
    headers = auth_headers(client, "alice")
    resp = client.patch("/api/v1/users/me", headers=headers, json={"full_name": "Alice A. Anders"})
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Alice A. Anders"
    # role should be unaffected when not supplied
    assert resp.json()["role"] == "Employee"
