"""
/api/v1 Formula Controller：Formula CRUD + 審核流程路由。
建立公式時需指定 department_id，查詢 / 更新 / 刪除則直接以 formula_id 操作。
"""
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.auth import get_current_user, require_role
from app.infra.db import get_db
from app.models.formulas import FormulaCreate, FormulaResponse, FormulaUpdate, ReviewAction
from app.repositories.department_repo import DepartmentRepo
from app.repositories.formula_repo import FormulaRepo
from app.repositories.user_repo import UserModel
from app.services.formula_service import FormulaService

# Imports for calculate and extract-variables
from app.models.scoring import (
    CalculateScoreRequest,
    ScoreResponse,
    ExtractVariablesRequest,
    ExtractVariablesResponse,
)
from app.infra.clients.gemini_client import GeminiClient
from app.repositories.formula_repo import FormulaRepo as FormulaRepoForScoring
from app.repositories.patient_field_repo import PatientFieldRepo
from app.services.ai.scoring_service import ScoringService

router = APIRouter(prefix="/v1")


def get_formula_service(db: Session = Depends(get_db)) -> FormulaService:
    return FormulaService(FormulaRepo(db), DepartmentRepo(db))


def get_scoring_service(db: Session = Depends(get_db)) -> ScoringService:
    return ScoringService(
        formula_repo=FormulaRepoForScoring(db),
        gemini_client=GeminiClient(),
        patient_field_repo=PatientFieldRepo(db),
    )


# ── 建立公式（admin / builder）
@router.post(
    "/departments/{department_id}/formulas",
    response_model=FormulaResponse,
    status_code=201,
    summary="在科別下建立公式",
    tags=["Formulas"],
)
def create_formula(
    department_id: int,
    data: FormulaCreate,
    current_user: UserModel = require_role("admin", "reviewer", "builder"),
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.create_formula(department_id, data, created_by=current_user.id)


# ── 列出所有公式（所有已登入使用者）
@router.get(
    "/formulas",
    response_model=List[FormulaResponse],
    summary="列出所有公式",
    tags=["Formulas"],
)
def list_formulas(
    department_id: Optional[int] = Query(None, description="依科別篩選"),
    include_inactive: bool = Query(False, description="是否包含已停用的公式"),
    current_user: UserModel = Depends(get_current_user),
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.list_formulas(department_id=department_id, include_inactive=include_inactive)


# ── 取得單一公式（所有已登入使用者）
@router.get(
    "/formulas/{formula_id}",
    response_model=FormulaResponse,
    summary="取得單一公式",
    tags=["Formulas"],
)
def get_formula(
    formula_id: int,
    current_user: UserModel = Depends(get_current_user),
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.get_formula(formula_id)


# ── 更新公式（admin / builder）
@router.put(
    "/formulas/{formula_id}",
    response_model=FormulaResponse,
    summary="更新公式",
    tags=["Formulas"],
)
def update_formula(
    formula_id: int,
    data: FormulaUpdate,
    current_user: UserModel = require_role("admin", "reviewer", "builder"),
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.update_formula(formula_id, data, user_role=current_user.role)


# ── 刪除公式（admin）
@router.delete(
    "/formulas/{formula_id}",
    status_code=204,
    summary="刪除公式",
    tags=["Formulas"],
)
def delete_formula(
    formula_id: int,
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: FormulaService = Depends(get_formula_service),
):
    svc.delete_formula(formula_id)

# ── 啟用/停用公式（admin）
@router.patch(
    "/formulas/{formula_id}/toggle",
    response_model=FormulaResponse,
    summary="啟用/停用公式",
    tags=["Formulas"],
)
def toggle_formula(
    formula_id: int,
    is_active: bool = Query(..., description="設為 true 啟用，false 停用"),
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.toggle_formula(formula_id, is_active)


# ── 審核流程 ─────────────────────────────────────────────────

# ── 提交審核（admin / builder）
@router.post(
    "/formulas/{formula_id}/submit-review",
    response_model=FormulaResponse,
    summary="提交公式進入審核",
    tags=["Formula Review"],
)
def submit_for_review(
    formula_id: int,
    current_user: UserModel = require_role("admin", "reviewer", "builder"),
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.submit_for_review(formula_id, user_role=current_user.role)


# ── 待審核列表（admin / reviewer）
@router.get(
    "/formulas-pending-review",
    response_model=List[FormulaResponse],
    summary="列出所有待審核公式",
    tags=["Formula Review"],
)
def list_pending_review(
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.list_pending_review()


# ── 核准公式（admin / reviewer）
@router.post(
    "/formulas/{formula_id}/approve",
    response_model=FormulaResponse,
    summary="核准公式",
    tags=["Formula Review"],
)
def approve_formula(
    formula_id: int,
    body: ReviewAction = None,
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: FormulaService = Depends(get_formula_service),
):
    comment = body.comment if body else None
    return svc.approve_formula(formula_id, reviewed_by=current_user.id, comment=comment)


# ── 駁回公式（admin / reviewer）
@router.post(
    "/formulas/{formula_id}/reject",
    response_model=FormulaResponse,
    summary="駁回公式",
    tags=["Formula Review"],
)
def reject_formula(
    formula_id: int,
    body: ReviewAction = None,
    current_user: UserModel = require_role("admin", "reviewer"),
    svc: FormulaService = Depends(get_formula_service),
):
    comment = body.comment if body else None
    return svc.reject_formula(formula_id, reviewed_by=current_user.id, comment=comment)


# ── 撤回審核（admin / builder）
@router.post(
    "/formulas/{formula_id}/revoke-review",
    response_model=FormulaResponse,
    summary="撤回審核中的公式（回到 draft）",
    tags=["Formula Review"],
)
def revoke_review(
    formula_id: int,
    current_user: UserModel = require_role("admin", "reviewer", "builder"),
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.revoke_review(formula_id)


# ── 計算分數（所有已登入使用者）
@router.post(
    "/formulas/calculate",
    response_model=ScoreResponse,
    summary="計算分數與風險等級",
    tags=["Formulas"],
)
def calculate_score(
    req: CalculateScoreRequest,
    current_user: UserModel = Depends(get_current_user),
    svc: ScoringService = Depends(get_scoring_service),
):
    return svc.calculate_score(req)

# ── 解析變數（所有已登入使用者）
@router.post(
    "/formulas/extract-variables",
    response_model=ExtractVariablesResponse,
    summary="解析 YAML 萃取所有變數定義",
    tags=["Formulas"],
)
def extract_variables(
    req: ExtractVariablesRequest,
    current_user: UserModel = Depends(get_current_user),
    svc: ScoringService = Depends(get_scoring_service),
):
    return svc.extract_variables(req)

# ── 轉換為 Blockly JSON AST
@router.post(
    "/formulas/convert-to-ast",
    response_model=Dict[str, Any],
    summary="將 YAML 轉換為 Blockly AST JSON",
    tags=["Formulas"],
)
def convert_to_ast(
    req: ExtractVariablesRequest,
    current_user: UserModel = Depends(get_current_user),
    svc: ScoringService = Depends(get_scoring_service),
):
    return svc.convert_to_ast(req)


# ── Prompt Registry（查詢 AI Prompt 區塊）
@router.get(
    "/prompts",
    response_model=List[Dict[str, Any]],
    summary="列出所有 AI Prompt 區塊",
    tags=["Prompts"],
)
def list_prompts(
    current_user: UserModel = Depends(get_current_user),
):
    from app.services.ai.prompts import PROMPT_REGISTRY
    return [
        {"key": key, **meta}
        for key, meta in PROMPT_REGISTRY.items()
    ]
