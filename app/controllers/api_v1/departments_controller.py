"""
/api/v1/departments Controller：Department CRUD 路由。
"""
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.auth import get_current_user, require_role
from app.infra.db import get_db
from app.schema.departments import (
    DepartmentCreate,
    DepartmentDetailResponse,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.repositories.department_repo import DepartmentRepo
from app.repositories.user_repo import UserModel
from app.services.department_service import DepartmentService

router = APIRouter(prefix="/v1/departments", tags=["Departments"])


def get_department_service(db: Session = Depends(get_db)) -> DepartmentService:
    return DepartmentService(DepartmentRepo(db))


@router.post("", response_model=DepartmentResponse, status_code=201, summary="建立科別")
def create_department(
    data: DepartmentCreate,
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: DepartmentService = Depends(get_department_service),
):
    return svc.create_department(data)


@router.get("", response_model=List[DepartmentResponse], summary="列出所有科別")
def list_departments(
    include_inactive: bool = Query(False, description="是否包含已停用的科別"),
    current_user: UserModel = Depends(get_current_user),
    svc: DepartmentService = Depends(get_department_service),
):
    return svc.list_departments(include_inactive=include_inactive)


@router.get("/{department_id}", response_model=DepartmentDetailResponse, summary="取得單一科別（含公式列表）")
def get_department(
    department_id: int,
    current_user: UserModel = Depends(get_current_user),
    svc: DepartmentService = Depends(get_department_service),
):
    return svc.get_department(department_id)


@router.put("/{department_id}", response_model=DepartmentResponse, summary="更新科別")
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: DepartmentService = Depends(get_department_service),
):
    return svc.update_department(department_id, data)


@router.patch("/{department_id}/toggle", response_model=DepartmentResponse, summary="啟用/停用科別")
def toggle_department(
    department_id: int,
    is_active: bool = Query(..., description="設為 true 啟用，false 停用"),
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: DepartmentService = Depends(get_department_service),
):
    return svc.toggle_department(department_id, is_active)


@router.delete("/{department_id}", status_code=204, summary="刪除科別")
def delete_department(
    department_id: int,
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: DepartmentService = Depends(get_department_service),
):
    svc.delete_department(department_id)
