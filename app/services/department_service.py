"""
Department Service：封裝 Department 的商業邏輯與用例流程。
"""
from typing import List

from app.common.exceptions import NotFoundException
from app.models.departments import (
    DepartmentCreate,
    DepartmentDetailResponse,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.repositories.department_repo import DepartmentRepo


class DepartmentService:
    """Department 商業邏輯層"""

    def __init__(self, repo: DepartmentRepo):
        self.repo = repo

    def create_department(self, data: DepartmentCreate) -> DepartmentResponse:
        db_dept = self.repo.create(data)
        return DepartmentResponse.model_validate(db_dept)

    def list_departments(self) -> List[DepartmentResponse]:
        db_depts = self.repo.list_all()
        return [DepartmentResponse.model_validate(d) for d in db_depts]

    def get_department(self, department_id: int) -> DepartmentDetailResponse:
        db_dept = self.repo.get_by_id(department_id)
        if db_dept is None:
            raise NotFoundException(f"Department {department_id} 不存在")
        return DepartmentDetailResponse.model_validate(db_dept)

    def update_department(self, department_id: int, data: DepartmentUpdate) -> DepartmentResponse:
        db_dept = self.repo.update(department_id, data)
        if db_dept is None:
            raise NotFoundException(f"Department {department_id} 不存在")
        return DepartmentResponse.model_validate(db_dept)

    def delete_department(self, department_id: int) -> None:
        success = self.repo.delete(department_id)
        if not success:
            raise NotFoundException(f"Department {department_id} 不存在")
