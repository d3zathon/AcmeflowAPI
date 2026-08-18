from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("/", response_model=List[schemas.ProjectOut], summary="List visible projects")
def list_projects(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Project)
    if current_user.role not in (models.RoleEnum.admin, models.RoleEnum.finance):
        query = query.filter(models.Project.department == current_user.department)
    return query.all()


@router.get("/{project_id}", response_model=schemas.ProjectOut, summary="Get a project (secure control)")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if current_user.role in (models.RoleEnum.admin, models.RoleEnum.finance):
        return project
    if project.department == current_user.department or project.manager_id == current_user.id:
        return project

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized for this project"
    )
