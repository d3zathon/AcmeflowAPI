import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class RoleEnum(str, enum.Enum):
    employee = "Employee"
    manager = "Manager"
    finance = "Finance"
    admin = "Admin"


class ExpenseStatus(str, enum.Enum):
    draft = "DRAFT"
    submitted = "SUBMITTED"
    approved = "APPROVED"
    rejected = "REJECTED"
    paid = "PAID"


class PaymentStatus(str, enum.Enum):
    pending = "PENDING"
    processing = "PROCESSING"
    completed = "COMPLETED"
    failed = "FAILED"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    full_name = Column(String(128), nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(SAEnum(RoleEnum), nullable=False, default=RoleEnum.employee)
    department = Column(String(64), nullable=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    manager = relationship("User", remote_side=[id], backref="direct_reports")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    code = Column(String(32), unique=True, nullable=False)
    department = Column(String(64))
    manager_id = Column(Integer, ForeignKey("users.id"))
    budget = Column(Float, default=0.0)

    manager = relationship("User")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    category = Column(String(64))
    description = Column(Text)
    status = Column(SAEnum(ExpenseStatus), default=ExpenseStatus.draft, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_reason = Column(String(256), nullable=True)

    owner = relationship("User", foreign_keys=[user_id])
    project = relationship("Project")
    payment = relationship("Payment", back_populates="expense", uselist=False)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String(32), default="ACH")
    account_reference = Column(String(64))
    status = Column(SAEnum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    expense = relationship("Expense", back_populates="payment")


class CompanySetting(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, nullable=False)
    value = Column(String(256), nullable=False)
    description = Column(String(256), nullable=True)
