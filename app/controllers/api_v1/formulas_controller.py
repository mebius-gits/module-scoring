"""
/api/v1 Formula Controller：Formula CRUD 路由。
建立公式時需指定 department_id，查詢 / 更新 / 刪除則直接以 formula_id 操作。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.infra.db import get_db
from app.models.formulas import FormulaCreate, FormulaResponse, FormulaUpdate
from app.repositories.department_repo import DepartmentRepo
from app.repositories.formula_repo import FormulaRepo
from app.repositories.formula_repo import FormulaRepo
from app.services.formula_service import FormulaService

# Imports for calculate and extract-variables
from app.models.scoring import (
    CalculateScoreRequest,
    ScoreResponse,
    ExtractVariablesRequest,
    ExtractVariablesResponse,
)
from app.controllers.ai_v1.scoring_controller import get_scoring_service
from app.services.ai.scoring_service import ScoringService

from typing import Dict, Any

router = APIRouter(prefix="/v1", tags=["Formulas"])


def get_formula_service(db: Session = Depends(get_db)) -> FormulaService:
    return FormulaService(FormulaRepo(db), DepartmentRepo(db))


# ── 建立公式（需在指定科別下）
@router.post(
    "/departments/{department_id}/formulas",
    response_model=FormulaResponse,
    status_code=201,
    summary="在科別下建立公式",
)
def create_formula(
    department_id: int,
    data: FormulaCreate,
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.create_formula(department_id, data)


# ── 列出所有公式（可選 filter by department_id）
@router.get(
    "/formulas",
    response_model=List[FormulaResponse],
    summary="列出所有公式",
)
def list_formulas(
    department_id: Optional[int] = Query(None, description="依科別篩選"),
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.list_formulas(department_id=department_id)


# ── 取得單一公式
@router.get(
    "/formulas/{formula_id}",
    response_model=FormulaResponse,
    summary="取得單一公式",
)
def get_formula(
    formula_id: int,
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.get_formula(formula_id)


# ── 更新公式
@router.put(
    "/formulas/{formula_id}",
    response_model=FormulaResponse,
    summary="更新公式",
)
def update_formula(
    formula_id: int,
    data: FormulaUpdate,
    svc: FormulaService = Depends(get_formula_service),
):
    return svc.update_formula(formula_id, data)


# ── 刪除公式
@router.delete(
    "/formulas/{formula_id}",
    status_code=204,
    summary="刪除公式",
)
def delete_formula(
    formula_id: int,
    svc: FormulaService = Depends(get_formula_service),
):
    svc.delete_formula(formula_id)

# ── 計算分數 (前移自 scoring_controller)
@router.post(
    "/formulas/calculate",
    response_model=ScoreResponse,
    summary="計算分數與風險等級",
)
def calculate_score(
    req: CalculateScoreRequest,
    svc: ScoringService = Depends(get_scoring_service),
):
    """
    提供 YAML 公式 (或 formula_id) 與輸入變數，計算分數與風險等級。
    """
    return svc.calculate_score(req)

# ── 解析變數 (前移自 scoring_controller)
@router.post(
    "/formulas/extract-variables",
    response_model=ExtractVariablesResponse,
    summary="解析 YAML 萃取所有變數定義",
)
def extract_variables(
    req: ExtractVariablesRequest,
    svc: ScoringService = Depends(get_scoring_service),
):
    """
    從 YAML 或 formula_id 解析出所有變數名稱與型態。
    前端可用此資訊動態生成輸入表單。
    """
    return svc.extract_variables(req)

# ── 轉換為 Blockly JSON AST ──────────────────────────────────
@router.post(
    "/formulas/convert-to-ast",
    response_model=Dict[str, Any],
    summary="將 YAML 轉換為 Blockly AST JSON",
)
def convert_to_ast(
    req: ExtractVariablesRequest,
    svc: ScoringService = Depends(get_scoring_service),
):
    """
    提供 YAML 公式 (或 formula_id)，將其轉換為舊版 Blockly React 應用程式期待的 JSON AST 結構。
    """
    return svc.convert_to_ast(req)
