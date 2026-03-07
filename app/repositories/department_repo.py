"""
Department Repository：封裝 Departments 的 SQLAlchemy ORM Model 與資料存取操作。
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import Session, relationship

from app.infra.db import Base
from app.models.departments import DepartmentCreate, DepartmentUpdate


class DepartmentModel(Base):
    """Departments ORM 資料表定義"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship: one department has many formulas
    formulas = relationship(
        "FormulaModel", back_populates="department", cascade="all, delete-orphan"
    )


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
