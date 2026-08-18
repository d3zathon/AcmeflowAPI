from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=schemas.UserOut, summary="Get my own profile")
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.patch(
    "/me",
    response_model=schemas.UserOut,
    summary="Update my own profile",
    description=(
        "Updates the caller's own profile. NOTE: this endpoint intentionally "
        "accepts a broader field set than it should (see ExpenseUpdateVulnerable-"
        "style schemas) -- see VULN-3 in the README."
    ),
)
def update_me(
    payload: schemas.UserUpdateVulnerable,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # --- VULN-3: Mass Assignment / Privilege Escalation ---------------------
    # `payload` (UserUpdateVulnerable) exposes `role` and `is_active`, and every
    # field the client supplies is applied verbatim with no server-side
    # allowlist. A caller can PATCH their own `role` to "Admin".
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
    # --------------------------------------------------------------------


@router.get(
    "/{user_id}",
    response_model=schemas.UserOut,
    summary="Get another user's profile (secure control)",
)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # SECURE: self, the user's manager, or an admin only.
    target = db.get(models.User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_self = current_user.id == user_id
    is_admin = current_user.role == models.RoleEnum.admin
    is_managing_manager = (
        current_user.role == models.RoleEnum.manager and target.manager_id == current_user.id
    )
    if not (is_self or is_admin or is_managing_manager):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this user",
        )
    return target
