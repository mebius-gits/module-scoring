"""
/api/v1/patient-fields Controller：PatientField CRUD 路由。
管理病人欄位名稱登錄（僅中繼資料，不含實際病人資料）。
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.auth import get_current_user, require_role
from app.infra.db import get_db
from app.schema.patient_fields import (
    PatientFieldCreate,
    PatientFieldResponse,
    PatientFieldUpdate,
)
from app.repositories.patient_field_repo import PatientFieldRepo
from app.repositories.user_repo import UserModel
from app.services.patient_field_service import PatientFieldService

router = APIRouter(prefix="/v1/patient-fields", tags=["Patient Fields"])


def get_patient_field_service(db: Session = Depends(get_db)) -> PatientFieldService:
    return PatientFieldService(PatientFieldRepo(db))


@router.get("", response_model=List[PatientFieldResponse], summary="列出所有病人欄位")
def list_patient_fields(
    current_user: UserModel = Depends(get_current_user),
    svc: PatientFieldService = Depends(get_patient_field_service),
):
    return svc.list_patient_fields()


@router.post("", response_model=PatientFieldResponse, status_code=201, summary="登錄新病人欄位")
def create_patient_field(
    data: PatientFieldCreate,
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: PatientFieldService = Depends(get_patient_field_service),
):
    return svc.create_patient_field(data)


@router.put("/{field_id}", response_model=PatientFieldResponse, summary="更新病人欄位")
def update_patient_field(
    field_id: int,
    data: PatientFieldUpdate,
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: PatientFieldService = Depends(get_patient_field_service),
):
    return svc.update_patient_field(field_id, data)


@router.delete("/{field_id}", status_code=204, summary="刪除病人欄位")
def delete_patient_field(
    field_id: int,
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: PatientFieldService = Depends(get_patient_field_service),
):
    svc.delete_patient_field(field_id)
