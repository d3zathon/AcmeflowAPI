from fastapi import FastAPI

from .database import Base, engine
from .routers import admin, auth, expenses, payments, projects, users

Base.metadata.create_all(bind=engine)

DESCRIPTION = """
**AcmeFlow API** is a realistic, deliberately vulnerable expense & finance
REST API built for local security testing (e.g. with APIAT).

It simulates a company with Employee / Manager / Finance / Admin roles,
projects, an expense approval workflow (`DRAFT -> SUBMITTED -> APPROVED ->
PAID`), and payment processing.

**This build intentionally contains a fixed set of authorization
vulnerabilities (BOLA, BFLA, mass assignment, workflow bypass, an admin
authorization bypass, and parameter tampering) alongside correctly-secured
control endpoints.** See the project README for the full list, reproduction
steps, and the `apiat/roles.yaml` file used to drive automated testing.

⚠️ Do not deploy this API outside of an isolated local lab environment.
"""

app = FastAPI(
    title="AcmeFlow API",
    description=DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(expenses.router)
app.include_router(payments.router)
app.include_router(admin.router)


@app.get("/health", tags=["meta"], summary="Health check")
def health():
    return {"status": "ok", "service": "AcmeFlow API"}
