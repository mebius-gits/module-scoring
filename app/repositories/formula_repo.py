"""
Formula Repository：封裝 Formulas 的 SQLAlchemy ORM Model 與資料存取操作。
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Session, relationship

from app.infra.db import Base
from app.models.formulas import FormulaCreate, FormulaUpdate


class FormulaModel(Base):
    """Formulas ORM 資料表定義"""
    __tablename__ = "formulas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    department_id = Column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    ast_data = Column(JSON, nullable=False)
    yaml_content = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    # ── 審核機制欄位 ────────────────────────────────────────
    status = Column(String(20), nullable=False, default="draft", server_default="draft")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    department = relationship("DepartmentModel", back_populates="formulas")
    creator = relationship("UserModel", foreign_keys=[created_by])
    reviewer = relationship("UserModel", foreign_keys=[reviewed_by])


class FormulaRepo:
    """Formula 資料存取物件 (DAO)"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, department_id: int, data: FormulaCreate, created_by: int | None = None) -> FormulaModel:
        formula = FormulaModel(
            department_id=department_id,
            name=data.name,
            description=data.description,
            ast_data=data.ast_data,
            yaml_content=data.yaml_content,
            status="draft",
            created_by=created_by,
        )
        self.db.add(formula)
        self.db.commit()
        self.db.refresh(formula)
        return formula

    def list_all(self, department_id: Optional[int] = None, include_inactive: bool = False) -> List[FormulaModel]:
        query = self.db.query(FormulaModel)
        if department_id is not None:
            query = query.filter(FormulaModel.department_id == department_id)
        if not include_inactive:
            query = query.filter(FormulaModel.is_active == True)
        return query.order_by(FormulaModel.id).all()

    def get_by_id(self, formula_id: int) -> Optional[FormulaModel]:
        return self.db.query(FormulaModel).filter(
            FormulaModel.id == formula_id
        ).first()

    def update(self, formula_id: int, data: FormulaUpdate) -> Optional[FormulaModel]:
        formula = self.get_by_id(formula_id)
        if formula is None:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(formula, field, value)
        self.db.commit()
        self.db.refresh(formula)
        return formula

    def set_active(self, formula_id: int, is_active: bool) -> Optional[FormulaModel]:
        formula = self.get_by_id(formula_id)
        if formula is None:
            return None
        formula.is_active = is_active
        self.db.commit()
        self.db.refresh(formula)
        return formula

    def delete(self, formula_id: int) -> bool:
        formula = self.get_by_id(formula_id)
        if formula is None:
            return False
        self.db.delete(formula)
        self.db.commit()
        return True

    # ── 審核相關 ──────────────────────────────────────────

    def set_status(self, formula_id: int, status: str) -> Optional[FormulaModel]:
        formula = self.get_by_id(formula_id)
        if formula is None:
            return None
        formula.status = status
        self.db.commit()
        self.db.refresh(formula)
        return formula

    def set_review(
        self,
        formula_id: int,
        status: str,
        reviewed_by: int,
        review_comment: Optional[str] = None,
    ) -> Optional[FormulaModel]:
        formula = self.get_by_id(formula_id)
        if formula is None:
            return None
        formula.status = status
        formula.reviewed_by = reviewed_by
        formula.reviewed_at = datetime.now(timezone.utc)
        formula.review_comment = review_comment
        self.db.commit()
        self.db.refresh(formula)
        return formula

    def list_by_status(self, status: str) -> List[FormulaModel]:
        return (
            self.db.query(FormulaModel)
            .filter(FormulaModel.status == status)
            .order_by(FormulaModel.id)
            .all()
        )
