from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db, get_or_404, require_roles

router = APIRouter(prefix="/api/v1/expenses", tags=["expenses"])


@router.post(
    "/",
    response_model=schemas.ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new DRAFT expense (secure control)",
)
def create_expense(
    payload: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # SECURE: ownership is derived server-side from the JWT. The client cannot
    # create an expense on someone else's behalf, unlike the mass-assignment
    # bug on PATCH /users/me.
    expense = models.Expense(
        user_id=current_user.id,
        project_id=payload.project_id,
        amount=payload.amount,
        currency=payload.currency,
        category=payload.category,
        description=payload.description,
        status=models.ExpenseStatus.draft,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/", response_model=List[schemas.ExpenseOut], summary="List expenses")
def list_expenses(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Expense)

    if current_user.role in (models.RoleEnum.finance, models.RoleEnum.admin):
        if user_id is not None:
            query = query.filter(models.Expense.user_id == user_id)
        return query.all()

    # --- VULN-7: Parameter Tampering ----------------------------------------
    # For Employee/Manager roles, a client-supplied `user_id` query parameter
    # is trusted directly instead of always being derived from the caller's
    # own identity (and, for managers, their direct reports). Any
    # authenticated employee or manager can pass `?user_id=<other id>` to
    # list another user's expenses.
    if user_id is not None:
        query = query.filter(models.Expense.user_id == user_id)
        return query.all()
    # -------------------------------------------------------------------

    if current_user.role == models.RoleEnum.manager:
        report_ids = [r.id for r in current_user.direct_reports] + [current_user.id]
        query = query.filter(models.Expense.user_id.in_(report_ids))
    else:
        query = query.filter(models.Expense.user_id == current_user.id)
    return query.all()


@router.get(
    "/{expense_id}",
    response_model=schemas.ExpenseOut,
    summary="Get an expense by ID",
)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    expense = get_or_404(db, models.Expense, expense_id)

    # --- VULN-1: BOLA (Broken Object Level Authorization) -------------------
    # No ownership or role check is performed here at all: any authenticated
    # user can read any expense by simply iterating IDs. Contrast this with
    # PUT /{expense_id} below, which DOES check ownership.
    return expense
    # -------------------------------------------------------------------


@router.put(
    "/{expense_id}",
    response_model=schemas.ExpenseOut,
    summary="Edit an expense (ownership enforced, workflow NOT enforced)",
)
def update_expense(
    expense_id: int,
    payload: schemas.ExpenseUpdateVulnerable,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    expense = get_or_404(db, models.Expense, expense_id)

    # Ownership IS correctly enforced here.
    if expense.user_id != current_user.id and current_user.role != models.RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You may only edit your own expenses"
        )

    # --- VULN-5: Workflow Bypass --------------------------------------------
    # `status` is part of ExpenseUpdateVulnerable and is applied verbatim with
    # no state-machine validation, so the owner of an expense can set
    # status=APPROVED or status=PAID directly, bypassing submit/approve/
    # reject/process entirely.
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(expense, field, value)
    # -------------------------------------------------------------------

    db.commit()
    db.refresh(expense)
    return expense


@router.post(
    "/{expense_id}/submit",
    response_model=schemas.ExpenseOut,
    summary="Submit a DRAFT expense (secure control)",
)
def submit_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    expense = get_or_404(db, models.Expense, expense_id)

    if expense.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner may submit this expense"
        )
    if expense.status != models.ExpenseStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit an expense in status {expense.status.value}",
        )

    expense.status = models.ExpenseStatus.submitted
    expense.submitted_at = datetime.utcnow()
    db.commit()
    db.refresh(expense)
    return expense


@router.post(
    "/{expense_id}/approve",
    response_model=schemas.ExpenseOut,
    summary="Approve a SUBMITTED expense (secure control)",
)
def approve_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(models.RoleEnum.manager, models.RoleEnum.admin)
    ),
):
    expense = get_or_404(db, models.Expense, expense_id)

    if expense.status != models.ExpenseStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve an expense in status {expense.status.value}",
        )

    owner = db.get(models.User, expense.user_id)

    # SECURE: role check (above, via require_roles) AND a scope check -- a
    # Manager may only approve expenses belonging to their own direct reports.
    if current_user.role == models.RoleEnum.manager and owner.manager_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Managers may only approve expenses for their direct reports",
        )

    expense.status = models.ExpenseStatus.approved
    expense.approved_at = datetime.utcnow()
    expense.approved_by = current_user.id
    db.add(
        models.Payment(
            expense_id=expense.id,
            amount=expense.amount,
            account_reference=f"ACCT-{owner.id:04d}-{expense.id:04d}",
        )
    )
    db.commit()
    db.refresh(expense)
    return expense


@router.post(
    "/{expense_id}/reject",
    response_model=schemas.ExpenseOut,
    summary="Reject a SUBMITTED expense",
)
def reject_expense(
    expense_id: int,
    payload: schemas.RejectRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    expense = get_or_404(db, models.Expense, expense_id)

    # --- VULN-2: BFLA (Broken Function Level Authorization) -----------------
    # Unlike /approve above, this endpoint performs NO role check whatsoever.
    # Any authenticated user -- including an Employee with no management
    # responsibility at all -- can reject any submitted expense.
    if expense.status != models.ExpenseStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject an expense in status {expense.status.value}",
        )

    expense.status = models.ExpenseStatus.rejected
    expense.rejected_reason = payload.reason
    db.commit()
    db.refresh(expense)
    return expense
    # -------------------------------------------------------------------
