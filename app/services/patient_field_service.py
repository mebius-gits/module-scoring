"""
PatientField Service：封裝 PatientField 的商業邏輯與用例流程。
"""
from typing import List

from app.common.exceptions import NotFoundException
from app.schema.patient_fields import (
    PatientFieldCreate,
    PatientFieldResponse,
    PatientFieldUpdate,
)
from app.repositories.patient_field_repo import PatientFieldRepo


class PatientFieldService:
    """PatientField 商業邏輯層"""

    def __init__(self, repo: PatientFieldRepo):
        self.repo = repo

    def create_patient_field(self, data: PatientFieldCreate) -> PatientFieldResponse:
        db_field = self.repo.create(data)
        return PatientFieldResponse.model_validate(db_field)

    def list_patient_fields(self) -> List[PatientFieldResponse]:
        db_fields = self.repo.list_all()
        return [PatientFieldResponse.model_validate(f) for f in db_fields]

    def update_patient_field(self, field_id: int, data: PatientFieldUpdate) -> PatientFieldResponse:
        db_field = self.repo.update(field_id, data)
        if db_field is None:
            raise NotFoundException(f"PatientField {field_id} 不存在")
        return PatientFieldResponse.model_validate(db_field)

    def delete_patient_field(self, field_id: int) -> None:
        success = self.repo.delete(field_id)
        if not success:
            raise NotFoundException(f"PatientField {field_id} 不存在")
