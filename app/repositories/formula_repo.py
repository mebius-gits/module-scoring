"""
Formula Repository：封裝 Formulas 的 SQLAlchemy ORM Model 與資料存取操作。
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.formulas import FormulaModel
from app.schema.formulas import FormulaCreate, FormulaUpdate


class FormulaRepo:
    """Formula 資料存取物件 (DAO)"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, department_id: int, data: FormulaCreate, created_by: int | None = None) -> FormulaModel:
        formula = FormulaModel(
            department_id=department_id,
            abbreviation=data.abbreviation,
            name=data.name,
            description=data.description,
            yaml_content=data.yaml_content,
            status="draft",
            created_by=created_by,
        )
        self.db.add(formula)
        self.db.commit()
        self.db.refresh(formula)
        return formula

    def list_all(self, department_id: Optional[int] = None, include_inactive: bool = False) -> List[FormulaModel]:
        query = self.db.query(FormulaModel).options(
            joinedload(FormulaModel.creator),
            joinedload(FormulaModel.reviewer),
        )
        if department_id is not None:
            query = query.filter(FormulaModel.department_id == department_id)
        if not include_inactive:
            query = query.filter(FormulaModel.is_active == True)
        return query.order_by(FormulaModel.id).all()

    def get_by_id(self, formula_id: int) -> Optional[FormulaModel]:
        return (
            self.db.query(FormulaModel)
            .options(
                joinedload(FormulaModel.creator),
                joinedload(FormulaModel.reviewer),
            )
            .filter(FormulaModel.id == formula_id)
            .first()
        )

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
            .options(
                joinedload(FormulaModel.creator),
                joinedload(FormulaModel.reviewer),
            )
            .filter(FormulaModel.status == status)
            .order_by(FormulaModel.id)
            .all()
        )
