from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db, get_or_404, require_roles

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.get("/{payment_id}", response_model=schemas.PaymentOut, summary="Get a payment by ID")
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    payment = get_or_404(db, models.Payment, payment_id)

    # --- VULN-4: Payment BOLA ------------------------------------------------
    # No role or ownership check is applied: any authenticated user (including
    # a regular Employee) can view any payment record by ID, exposing amounts
    # and account_reference for other employees' payouts. Contrast this with
    # POST /{payment_id}/process below, which correctly restricts by role AND
    # validates expense/payment state.
    return payment
    # -------------------------------------------------------------------


@router.post(
    "/{payment_id}/process",
    response_model=schemas.PaymentOut,
    summary="Process a PENDING payment (secure control)",
)
def process_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_roles(models.RoleEnum.finance, models.RoleEnum.admin)
    ),
):
    payment = get_or_404(db, models.Payment, payment_id)
    expense = db.get(models.Expense, payment.expense_id)

    if expense.status != models.ExpenseStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Expense must be APPROVED before its payment can be processed",
        )
    if payment.status != models.PaymentStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Payment is already in status {payment.status.value}",
        )

    payment.status = models.PaymentStatus.completed
    payment.processed_by = current_user.id
    payment.processed_at = datetime.utcnow()
    expense.status = models.ExpenseStatus.paid

    db.commit()
    db.refresh(payment)
    return payment
