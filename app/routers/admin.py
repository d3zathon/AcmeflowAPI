from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db, get_or_404, require_roles

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=List[schemas.UserOut],
    summary="List all users (secure control)",
)
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(models.RoleEnum.admin)),
):
    return db.query(models.User).all()


@router.patch(
    "/users/{user_id}/role",
    response_model=schemas.UserOut,
    summary="Change a user's role (secure control)",
)
def change_role(
    user_id: int,
    payload: schemas.RoleChangeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles(models.RoleEnum.admin)),
):
    target = get_or_404(db, models.User, user_id)
    target.role = payload.role
    db.commit()
    db.refresh(target)
    return target


@router.get(
    "/settings",
    response_model=List[schemas.SettingOut],
    summary="List company settings",
)
def get_settings(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    # --- VULN-6: Administrative Authorization Bypass -------------------------
    # This check is written as a DENYLIST ("block Employees") instead of an
    # ALLOWLIST ("require Admin", as used correctly by /admin/users above).
    # As a result, Manager and Finance roles -- which were never intended to
    # have admin access -- can also read (and, below, write) settings that
    # should be Admin-only.
    if current_user.role == models.RoleEnum.employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees may not view company settings",
        )
    return db.query(models.CompanySetting).all()
    # -------------------------------------------------------------------


@router.put(
    "/settings/{key}",
    response_model=schemas.SettingOut,
    summary="Update a company setting",
)
def update_setting(
    key: str,
    payload: schemas.SettingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Same denylist bug as GET /settings above -- see VULN-6.
    if current_user.role == models.RoleEnum.employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees may not modify company settings",
        )
    setting = db.query(models.CompanySetting).filter(models.CompanySetting.key == key).first()
    if setting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found")
    setting.value = payload.value
    db.commit()
    db.refresh(setting)
    return setting
