from .conftest import USER_IDS, auth_headers


def test_vuln_admin_bypass_manager_can_read_settings(client):
    """VULN-6: /admin/settings uses a denylist (blocks Employee) not an allowlist (require Admin)."""
    headers = auth_headers(client, "bob")  # Manager, not Admin
    resp = client.get("/api/v1/admin/settings", headers=headers)
    assert resp.status_code == 200  # <- should be 403 in a fixed build


def test_vuln_admin_bypass_finance_can_write_settings(client):
    headers = auth_headers(client, "david")  # Finance, not Admin
    resp = client.put(
        "/api/v1/admin/settings/company_name", headers=headers, json={"value": "Tampered Inc."}
    )
    assert resp.status_code == 200  # <- should be 403 in a fixed build
    assert resp.json()["value"] == "Tampered Inc."


def test_employees_are_still_blocked_from_settings(client):
    """The denylist DOES correctly block Employee -- illustrating a partial fix."""
    headers = auth_headers(client, "alice")
    resp = client.get("/api/v1/admin/settings", headers=headers)
    assert resp.status_code == 403


def test_secure_control_admin_user_list_blocks_manager(client):
    headers = auth_headers(client, "bob")
    resp = client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 403


def test_secure_control_admin_can_list_users(client):
    headers = auth_headers(client, "admin")
    resp = client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 7


def test_secure_control_only_admin_can_change_roles(client):
    bob_headers = auth_headers(client, "bob")
    resp = client.patch(
        f"/api/v1/admin/users/{USER_IDS['alice']}/role", headers=bob_headers, json={"role": "Finance"}
    )
    assert resp.status_code == 403

    admin_headers = auth_headers(client, "admin")
    resp2 = client.patch(
        f"/api/v1/admin/users/{USER_IDS['alice']}/role", headers=admin_headers, json={"role": "Finance"}
    )
    assert resp2.status_code == 200
    assert resp2.json()["role"] == "Finance"
