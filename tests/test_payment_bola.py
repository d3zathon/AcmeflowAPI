from .conftest import auth_headers


def test_vuln_payment_bola_employee_reads_others_payment(client):
    """VULN-4: GET /api/v1/payments/{id} has no role/ownership check."""
    headers = auth_headers(client, "alice")  # not finance/admin, not frank
    resp = client.get("/api/v1/payments/2", headers=headers)  # frank's pending payment
    assert resp.status_code == 200  # <- should be 403 in a fixed build
    body = resp.json()
    assert body["expense_id"] == 6
    assert "account_reference" in body  # sensitive financial data exposed


def test_secure_control_only_finance_or_admin_can_process(client):
    headers = auth_headers(client, "alice")
    resp = client.post("/api/v1/payments/2/process", headers=headers)
    assert resp.status_code == 403


def test_secure_control_finance_can_process_pending_payment(client):
    headers = auth_headers(client, "david")  # Finance
    resp = client.post("/api/v1/payments/2/process", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"

    expense_resp = client.get("/api/v1/expenses/6", headers=headers)
    assert expense_resp.json()["status"] == "PAID"


def test_secure_control_cannot_reprocess_completed_payment(client):
    headers = auth_headers(client, "david")
    resp = client.post("/api/v1/payments/1/process", headers=headers)  # already COMPLETED
    assert resp.status_code == 409
