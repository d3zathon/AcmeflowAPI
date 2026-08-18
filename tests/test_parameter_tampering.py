from .conftest import USER_IDS, auth_headers


def test_secure_baseline_employee_sees_only_own_expenses(client):
    headers = auth_headers(client, "alice")
    resp = client.get("/api/v1/expenses/", headers=headers)
    assert resp.status_code == 200
    owner_ids = {e["user_id"] for e in resp.json()}
    assert owner_ids == {USER_IDS["alice"]}


def test_vuln_parameter_tampering_employee_lists_others_expenses(client):
    """VULN-7: the `user_id` query param is trusted directly for non-privileged roles."""
    headers = auth_headers(client, "alice")
    resp = client.get(
        "/api/v1/expenses/", headers=headers, params={"user_id": USER_IDS["carol"]}
    )
    assert resp.status_code == 200  # <- should ignore/reject this param for an Employee
    owner_ids = {e["user_id"] for e in resp.json()}
    assert owner_ids == {USER_IDS["carol"]}


def test_vuln_parameter_tampering_also_affects_managers(client):
    """bob manages alice/carol, NOT frank -- but the tampered param ignores that scope."""
    headers = auth_headers(client, "bob")
    resp = client.get(
        "/api/v1/expenses/", headers=headers, params={"user_id": USER_IDS["frank"]}
    )
    assert resp.status_code == 200  # <- should be blocked/scoped in a fixed build
    owner_ids = {e["user_id"] for e in resp.json()}
    assert owner_ids == {USER_IDS["frank"]}


def test_secure_control_manager_default_scope_is_direct_reports_only(client):
    headers = auth_headers(client, "bob")
    resp = client.get("/api/v1/expenses/", headers=headers)  # no tampered param
    assert resp.status_code == 200
    owner_ids = {e["user_id"] for e in resp.json()}
    assert owner_ids <= {USER_IDS["bob"], USER_IDS["alice"], USER_IDS["carol"]}
    assert USER_IDS["frank"] not in owner_ids
