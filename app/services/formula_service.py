"""
Formula Service：封裝 Formula 的商業邏輯與用例流程。
"""
from typing import List, Optional

from app.common.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.models.formulas import FormulaCreate, FormulaResponse, FormulaUpdate
from app.repositories.department_repo import DepartmentRepo
from app.repositories.formula_repo import FormulaRepo


class FormulaService:
    """Formula 商業邏輯層"""

    def __init__(self, repo: FormulaRepo, department_repo: DepartmentRepo):
        self.repo = repo
        self.department_repo = department_repo

    def create_formula(self, department_id: int, data: FormulaCreate, created_by: int | None = None) -> FormulaResponse:
        dept = self.department_repo.get_by_id(department_id)
        if dept is None:
            raise NotFoundException(f"Department {department_id} 不存在")
        db_formula = self.repo.create(department_id, data, created_by=created_by)
        return FormulaResponse.model_validate(db_formula)

    def list_formulas(self, department_id: Optional[int] = None, include_inactive: bool = False) -> List[FormulaResponse]:
        db_formulas = self.repo.list_all(department_id=department_id, include_inactive=include_inactive)
        return [FormulaResponse.model_validate(f) for f in db_formulas]

    def get_formula(self, formula_id: int) -> FormulaResponse:
        db_formula = self.repo.get_by_id(formula_id)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        return FormulaResponse.model_validate(db_formula)

    def update_formula(self, formula_id: int, data: FormulaUpdate, user_role: str = "admin") -> FormulaResponse:
        db_formula = self.repo.get_by_id(formula_id)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        # 只有 draft / rejected 狀態才能編輯（admin 可略過）
        if user_role != "admin" and db_formula.status not in ("draft", "rejected"):
            raise ValidationException(f"公式目前狀態為 {db_formula.status}，無法編輯")
        updated = self.repo.update(formula_id, data)
        return FormulaResponse.model_validate(updated)

    def toggle_formula(self, formula_id: int, is_active: bool) -> FormulaResponse:
        db_formula = self.repo.set_active(formula_id, is_active)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        return FormulaResponse.model_validate(db_formula)

    def delete_formula(self, formula_id: int) -> None:
        success = self.repo.delete(formula_id)
        if not success:
            raise NotFoundException(f"Formula {formula_id} 不存在")

    # ── 審核流程 ─────────────────────────────────────────────

    def submit_for_review(self, formula_id: int, user_role: str = "builder") -> FormulaResponse:
        """builder/admin 提交公式進入審核"""
        db_formula = self.repo.get_by_id(formula_id)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        if db_formula.status not in ("draft", "rejected"):
            raise ValidationException(f"只有 draft 或 rejected 狀態的公式才能提交審核，目前為 {db_formula.status}")
        result = self.repo.set_status(formula_id, "pending_review")
        return FormulaResponse.model_validate(result)

    def list_pending_review(self) -> List[FormulaResponse]:
        """列出所有待審核公式"""
        db_formulas = self.repo.list_by_status("pending_review")
        return [FormulaResponse.model_validate(f) for f in db_formulas]

    def approve_formula(self, formula_id: int, reviewed_by: int, comment: Optional[str] = None) -> FormulaResponse:
        """reviewer/admin 核准公式"""
        db_formula = self.repo.get_by_id(formula_id)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        if db_formula.status != "pending_review":
            raise ValidationException(f"只有 pending_review 狀態的公式才能核准，目前為 {db_formula.status}")
        result = self.repo.set_review(formula_id, "approved", reviewed_by, comment)
        return FormulaResponse.model_validate(result)

    def reject_formula(self, formula_id: int, reviewed_by: int, comment: Optional[str] = None) -> FormulaResponse:
        """reviewer/admin 駁回公式"""
        db_formula = self.repo.get_by_id(formula_id)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        if db_formula.status != "pending_review":
            raise ValidationException(f"只有 pending_review 狀態的公式才能駁回，目前為 {db_formula.status}")
        result = self.repo.set_review(formula_id, "rejected", reviewed_by, comment)
        return FormulaResponse.model_validate(result)

    def revoke_review(self, formula_id: int) -> FormulaResponse:
        """builder/admin 撤回審核中的公式"""
        db_formula = self.repo.get_by_id(formula_id)
        if db_formula is None:
            raise NotFoundException(f"Formula {formula_id} 不存在")
        if db_formula.status != "pending_review":
            raise ValidationException(f"只有 pending_review 狀態的公式才能撤回，目前為 {db_formula.status}")
        result = self.repo.set_status(formula_id, "draft")
        return FormulaResponse.model_validate(result)
