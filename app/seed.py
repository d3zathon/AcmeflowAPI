"""Deterministic seed data for the AcmeFlow API lab."""
import argparse
from datetime import datetime, timedelta

from sqlalchemy import text

from . import models
from .database import Base, SessionLocal, engine
from .security import get_password_hash


def clear_all(db):
    """Reset lab data and PostgreSQL identity sequences."""
    db.execute(text(
        "TRUNCATE TABLE payments, expenses, projects, users, company_settings "
        "RESTART IDENTITY CASCADE"
    ))
    db.commit()


def seed_all(db, reset: bool = False):
    if reset:
        clear_all(db)
    elif db.query(models.User).first() is not None:
        return

    def mk_user(username, email, full_name, role, department, password):
        u = models.User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            department=department,
            hashed_password=get_password_hash(password),
            is_active=True,
        )
        db.add(u)
        return u

    admin = mk_user("admin", "admin@acmeflow.test", "Aiden Admin", models.RoleEnum.admin, "Operations", "Admin#2024")
    bob = mk_user("bob", "bob@acmeflow.test", "Bob Bergstrom", models.RoleEnum.manager, "Engineering", "Bob#2024")
    erin = mk_user("erin", "erin@acmeflow.test", "Erin Ellison", models.RoleEnum.manager, "Sales", "Erin#2024")
    david = mk_user("david", "david@acmeflow.test", "David Diaz", models.RoleEnum.finance, "Finance", "David#2024")
    db.flush()

    alice = mk_user("alice", "alice@acmeflow.test", "Alice Anders", models.RoleEnum.employee, "Engineering", "Alice#2024")
    carol = mk_user("carol", "carol@acmeflow.test", "Carol Chen", models.RoleEnum.employee, "Engineering", "Carol#2024")
    frank = mk_user("frank", "frank@acmeflow.test", "Frank Foster", models.RoleEnum.employee, "Sales", "Frank#2024")
    db.flush()

    alice.manager_id = bob.id
    carol.manager_id = bob.id
    frank.manager_id = erin.id
    db.commit()

    proj_eng = models.Project(name="Platform Migration", code="P-ENG-001", department="Engineering", manager_id=bob.id, budget=250000)
    proj_sales = models.Project(name="Q3 Sales Push", code="P-SALES-001", department="Sales", manager_id=erin.id, budget=80000)
    db.add_all([proj_eng, proj_sales])
    db.commit()

    now = datetime.utcnow()
    e1 = models.Expense(user_id=alice.id, project_id=proj_eng.id, amount=42.50, currency="USD", category="Meals", description="Team lunch with vendor", status=models.ExpenseStatus.draft, created_at=now)
    e2 = models.Expense(user_id=alice.id, project_id=proj_eng.id, amount=310.00, currency="USD", category="Travel", description="Conference train tickets", status=models.ExpenseStatus.submitted, created_at=now-timedelta(days=2), submitted_at=now-timedelta(days=2))
    e3 = models.Expense(user_id=alice.id, project_id=proj_eng.id, amount=120.00, currency="USD", category="Software", description="Annual IDE license", status=models.ExpenseStatus.paid, created_at=now-timedelta(days=20), submitted_at=now-timedelta(days=19), approved_at=now-timedelta(days=18), approved_by=bob.id)
    e4 = models.Expense(user_id=carol.id, project_id=proj_eng.id, amount=88.20, currency="USD", category="Meals", description="Client dinner", status=models.ExpenseStatus.submitted, created_at=now-timedelta(days=1), submitted_at=now-timedelta(days=1))
    e5 = models.Expense(user_id=frank.id, project_id=proj_sales.id, amount=560.00, currency="USD", category="Travel", description="Flight for sales trip", status=models.ExpenseStatus.submitted, created_at=now-timedelta(days=3), submitted_at=now-timedelta(days=3))
    e6 = models.Expense(user_id=frank.id, project_id=proj_sales.id, amount=95.00, currency="USD", category="Meals", description="Prospect lunch", status=models.ExpenseStatus.approved, created_at=now-timedelta(days=5), submitted_at=now-timedelta(days=5), approved_at=now-timedelta(days=4), approved_by=erin.id)
    db.add_all([e1, e2, e3, e4, e5, e6])
    db.commit()

    p1 = models.Payment(expense_id=e3.id, amount=e3.amount, method="ACH", account_reference=f"ACCT-{alice.id:04d}-{e3.id:04d}", status=models.PaymentStatus.completed, processed_by=david.id, processed_at=now-timedelta(days=17))
    p2 = models.Payment(expense_id=e6.id, amount=e6.amount, method="ACH", account_reference=f"ACCT-{frank.id:04d}-{e6.id:04d}", status=models.PaymentStatus.pending)
    db.add_all([p1, p2])
    db.commit()

    settings_seed = [
        ("company_name", "AcmeFlow Inc.", "Legal company name"),
        ("approval_threshold_usd", "5000", "Expenses above this amount require additional review (informational only)"),
        ("fiscal_year_start", "January", "Start of the fiscal year"),
        ("payment_processor", "MockACH", "Simulated payment processor used by this lab"),
    ]
    for key, value, desc in settings_seed:
        db.add(models.CompanySetting(key=key, value=value, description=desc))
    db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the AcmeFlow API database")
    parser.add_argument("--reset", action="store_true", help="Clear existing data first")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        seed_all(session, reset=args.reset)
        print("AcmeFlow API: seed complete.")
    finally:
        session.close()
