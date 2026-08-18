from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import ExpenseStatus, PaymentStatus, RoleEnum


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str
    role: RoleEnum
    department: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: bool


class UserUpdateSecure(BaseModel):
    """What a self-service profile update SHOULD look like."""

    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None


class UserUpdateVulnerable(BaseModel):
    """
    VULNERABLE SCHEMA (used by PATCH /api/v1/users/me).

    `role` and `is_active` should never be settable by the user themselves --
    including them here (and applying every submitted field verbatim in the
    handler) creates a mass-assignment / privilege-escalation vulnerability.
    """

    full_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    department: Optional[str] = None
    manager_id: Optional[int] = None
    budget: float


class ExpenseCreate(BaseModel):
    project_id: Optional[int] = None
    amount: float = Field(gt=0)
    currency: str = "USD"
    category: str
    description: Optional[str] = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    project_id: Optional[int] = None
    amount: float
    currency: str
    category: Optional[str] = None
    description: Optional[str] = None
    status: ExpenseStatus
    created_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    rejected_reason: Optional[str] = None


class ExpenseUpdateVulnerable(BaseModel):
    """
    VULNERABLE SCHEMA (used by PUT /api/v1/expenses/{id}).

    `status` is exposed as a directly client-settable field. The handler does
    NOT re-validate the DRAFT -> SUBMITTED -> APPROVED -> PAID state machine
    for it, so an owner can self-approve or self-mark-paid their own expense
    (workflow bypass).
    """

    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ExpenseStatus] = None


class RejectRequest(BaseModel):
    reason: str


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    expense_id: int
    amount: float
    method: str
    account_reference: str
    status: PaymentStatus
    processed_by: Optional[int] = None
    processed_at: Optional[datetime] = None
    created_at: datetime


class RoleChangeRequest(BaseModel):
    role: RoleEnum


class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    value: str
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    value: str
