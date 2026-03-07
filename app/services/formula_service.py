"""
Formula Service：封裝 Formula 的商業邏輯與用例流程。
"""
from typing import List, Optional

from app.common.exceptions import NotFoundException
from app.models.formulas import FormulaCreate, FormulaResponse, FormulaUpdate
from app.repositories.department_repo import DepartmentRepo
from app.repositories.formula_repo import FormulaRepo


class FormulaService:
    """Formula 商業邏輯層"""

    def __init__(self, repo: FormulaRepo, department_repo: DepartmentRepo):
        self.repo = repo
        self.department_repo = department_repo

    def create_formula(self, department_id: int, data: FormulaCreate) -> FormulaResponse:
        # 先確認科別存在
        dept = self.department_repo.get_by_id(department_id)
        if dept is None:
            raise NotFoundException(f"Department {department_id} 不存在")
        db_formula = self.repo.create(department_id, data)
        return FormulaResponse.model_validate(db_formula)

    def list_formulas(self, department_id: Optional[int] = None, include_inactive: bool = False) -> List[FormulaResponse]:
        db_formulas = self.repo.list_all(department_id=department_id, include_inactive=include_inactive)
        return [FormulaResponse.model_validate(f) for f in db_formulas]

    def get_formula(self, formula_id: int) -> FormulaResponse:
        db_formula = self.repo.get_by_id(formula_id)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        return FormulaResponse.model_validate(db_formula)

    def update_formula(self, formula_id: int, data: FormulaUpdate) -> FormulaResponse:
        db_formula = self.repo.update(formula_id, data)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        return FormulaResponse.model_validate(db_formula)

    def toggle_formula(self, formula_id: int, is_active: bool) -> FormulaResponse:
        db_formula = self.repo.set_active(formula_id, is_active)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        return FormulaResponse.model_validate(db_formula)

    def delete_formula(self, formula_id: int) -> None:
        success = self.repo.delete(formula_id)
        if not success:
            raise NotFoundException(f"Formula {formula_id} 不存在")
