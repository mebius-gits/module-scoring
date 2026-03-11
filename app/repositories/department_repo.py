"""
Department Repository：封裝 Departments 的 SQLAlchemy ORM Model 與資料存取操作。
"""
from typing import List, Optional

from sqlalchemy.orm import Session
from app.models.departments import DepartmentModel
from app.schema.departments import DepartmentCreate, DepartmentUpdate


class DepartmentRepo:
    """Department 資料存取物件 (DAO)"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: DepartmentCreate) -> DepartmentModel:
        dept = DepartmentModel(name=data.name, description=data.description)
        self.db.add(dept)
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def list_all(self, include_inactive: bool = False) -> List[DepartmentModel]:
        query = self.db.query(DepartmentModel)
        if not include_inactive:
            query = query.filter(DepartmentModel.is_active == True)
        return query.order_by(DepartmentModel.id).all()

    def get_by_id(self, department_id: int) -> Optional[DepartmentModel]:
        return self.db.query(DepartmentModel).filter(
            DepartmentModel.id == department_id
        ).first()

    def update(self, department_id: int, data: DepartmentUpdate) -> Optional[DepartmentModel]:
        dept = self.get_by_id(department_id)
        if dept is None:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(dept, field, value)
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def set_active(self, department_id: int, is_active: bool) -> Optional[DepartmentModel]:
        dept = self.get_by_id(department_id)
        if dept is None:
            return None
        dept.is_active = is_active
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def delete(self, department_id: int) -> bool:
        dept = self.get_by_id(department_id)
        if dept is None:
            return False
        self.db.delete(dept)
        self.db.commit()
        return True
