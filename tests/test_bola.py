from .conftest import USER_IDS, auth_headers


def test_owner_can_view_own_expense(client):
    headers = auth_headers(client, "alice")
    resp = client.get("/api/v1/expenses/1", headers=headers)  # alice's own DRAFT expense
    assert resp.status_code == 200
    assert resp.json()["user_id"] == USER_IDS["alice"]


def test_vuln_bola_cross_user_expense_read(client):
    """VULN-1: GET /api/v1/expenses/{id} has no ownership/role check."""
    headers = auth_headers(client, "alice")
    # Expense 4 belongs to carol, not alice.
    resp = client.get("/api/v1/expenses/4", headers=headers)
    assert resp.status_code == 200  # <- should be 403/404 in a fixed build
    assert resp.json()["user_id"] == USER_IDS["carol"]


def test_vuln_bola_finance_data_not_needed_to_read(client):
    """A plain Employee (frank) can read another employee's (carol's) expense."""
    headers = auth_headers(client, "frank")
    resp = client.get("/api/v1/expenses/4", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["user_id"] == USER_IDS["carol"]


def test_secure_control_user_lookup_blocks_unrelated_employee(client):
    """GET /api/v1/users/{id} correctly enforces self/manager/admin scoping."""
    headers = auth_headers(client, "alice")
    # frank is not alice, not her manager, and alice is not admin.
    resp = client.get(f"/api/v1/users/{USER_IDS['frank']}", headers=headers)
    assert resp.status_code == 403


def test_secure_control_manager_can_view_direct_report(client):
    headers = auth_headers(client, "bob")  # bob manages alice
    resp = client.get(f"/api/v1/users/{USER_IDS['alice']}", headers=headers)
    assert resp.status_code == 200


def test_secure_control_manager_cannot_view_non_report(client):
    headers = auth_headers(client, "bob")  # bob does NOT manage frank
    resp = client.get(f"/api/v1/users/{USER_IDS['frank']}", headers=headers)
    assert resp.status_code == 403
