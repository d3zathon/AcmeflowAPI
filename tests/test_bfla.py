from .conftest import auth_headers


def test_vuln_bfla_employee_can_reject_others_expense(client):
    """VULN-2: POST /api/v1/expenses/{id}/reject has no role check at all."""
    headers = auth_headers(client, "alice")  # plain Employee, not carol's manager
    resp = client.post(
        "/api/v1/expenses/4/reject",  # carol's SUBMITTED expense
        headers=headers,
        json={"reason": "rejected by an unrelated employee"},
    )
    assert resp.status_code == 200  # <- should be 403 in a fixed build
    assert resp.json()["status"] == "REJECTED"


def test_secure_control_employee_cannot_approve(client):
    headers = auth_headers(client, "alice")
    resp = client.post("/api/v1/expenses/4/approve", headers=headers)
    assert resp.status_code == 403


def test_secure_control_manager_cannot_approve_outside_scope(client):
    """bob manages alice/carol, NOT frank -- approving frank's expense must fail."""
    headers = auth_headers(client, "bob")
    resp = client.post("/api/v1/expenses/5/approve", headers=headers)  # frank's SUBMITTED expense
    assert resp.status_code == 403


def test_secure_control_correct_manager_can_approve(client):
    """erin manages frank -- this should succeed."""
    headers = auth_headers(client, "erin")
    resp = client.post("/api/v1/expenses/5/approve", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"
