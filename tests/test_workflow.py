from .conftest import auth_headers


def test_vuln_workflow_bypass_self_approve(client):
    """VULN-5: PUT /api/v1/expenses/{id} accepts a raw `status` field."""
    headers = auth_headers(client, "alice")

    created = client.post(
        "/api/v1/expenses/",
        headers=headers,
        json={"amount": 999.99, "category": "Travel", "description": "Suspiciously large trip"},
    )
    assert created.status_code == 201
    expense_id = created.json()["id"]
    assert created.json()["status"] == "DRAFT"

    # Skips submit AND approve entirely.
    bypass = client.put(
        f"/api/v1/expenses/{expense_id}", headers=headers, json={"status": "APPROVED"}
    )
    assert bypass.status_code == 200  # <- should reject client-supplied status transitions
    assert bypass.json()["status"] == "APPROVED"

    bypass_paid = client.put(
        f"/api/v1/expenses/{expense_id}", headers=headers, json={"status": "PAID"}
    )
    assert bypass_paid.status_code == 200
    assert bypass_paid.json()["status"] == "PAID"


def test_secure_control_cannot_edit_others_expense(client):
    headers = auth_headers(client, "carol")
    resp = client.put("/api/v1/expenses/1", headers=headers, json={"amount": 1.0})  # alice's expense
    assert resp.status_code == 403


def test_secure_control_cannot_submit_twice(client):
    headers = auth_headers(client, "alice")
    resp = client.post("/api/v1/expenses/2/submit", headers=headers)  # already SUBMITTED
    assert resp.status_code == 409


def test_happy_path_full_lifecycle(client):
    """The full DRAFT -> SUBMITTED -> APPROVED -> PAID path via the correct endpoints."""
    alice_headers = auth_headers(client, "alice")
    bob_headers = auth_headers(client, "bob")
    david_headers = auth_headers(client, "david")

    created = client.post(
        "/api/v1/expenses/",
        headers=alice_headers,
        json={"amount": 75.00, "category": "Meals", "description": "Client coffee"},
    )
    assert created.status_code == 201
    expense_id = created.json()["id"]

    submitted = client.post(f"/api/v1/expenses/{expense_id}/submit", headers=alice_headers)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "SUBMITTED"

    approved = client.post(f"/api/v1/expenses/{expense_id}/approve", headers=bob_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"

    # Payment auto-created on approval; find it via the expense listing scoped to finance.
    all_expenses = client.get("/api/v1/expenses/", headers=david_headers).json()
    payment_ids = [e["id"] for e in all_expenses if e["id"] == expense_id]
    assert payment_ids, "expected the newly approved expense to be visible to finance"

    # Payments are keyed separately; walk IDs 1..N to find the matching one deterministically
    # (in this lab there is exactly one new payment after the fixed seed set of 2).
    new_payment = client.get("/api/v1/payments/3", headers=david_headers)
    assert new_payment.status_code == 200
    assert new_payment.json()["expense_id"] == expense_id
    assert new_payment.json()["status"] == "PENDING"

    processed = client.post("/api/v1/payments/3/process", headers=david_headers)
    assert processed.status_code == 200
    assert processed.json()["status"] == "COMPLETED"

    final = client.get(f"/api/v1/expenses/{expense_id}", headers=alice_headers)
    assert final.json()["status"] == "PAID"
