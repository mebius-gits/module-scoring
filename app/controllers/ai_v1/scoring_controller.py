"""
/ai/v1/scoring Controller：混合模式聊天（一般對話 + 公式生成）端點。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.auth import require_role
from app.infra.db import get_db
from app.infra.clients.gemini_client import GeminiClient
from app.models.scoring import (
    ChatRequest,
    ChatResponse,
)
from app.repositories.formula_repo import FormulaRepo
from app.repositories.patient_field_repo import PatientFieldRepo
from app.repositories.user_repo import UserModel
from app.services.ai.scoring_service import ScoringService

router = APIRouter(
    prefix="/v1/ai",
    tags=["AI Chat"],
)


def get_scoring_service(db: Session = Depends(get_db)) -> ScoringService:
    """建立 ScoringService 並注入所有依賴"""
    return ScoringService(
        formula_repo=FormulaRepo(db),
        gemini_client=GeminiClient(),
    )


# ── Mixed-mode Chat（聊天 + 公式生成）──────────────────────────


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="混合模式聊天（一般對話 + 公式生成）",
)
def chat(
    req: ChatRequest,
    current_user: UserModel = require_role("admin", "reviewer", "builder"),
    db: Session = Depends(get_db),
    svc: ScoringService = Depends(get_scoring_service),
):
    """
    混合模式聊天端點：
    - AI 自動判斷使用者訊息是一般對話或公式生成請求
    - 自動從 DB 讀取已登錄的病人欄位（patient_fields），提供 AI 變數名稱提示
    - 若為公式請求：回傳對話回覆 + 生成的 YAML 公式字串
    - 若為一般對話：僅回傳 AI 對話回覆（繁體中文）
    """
    # 從 DB 讀取已登錄的病人欄位
    repo = PatientFieldRepo(db)
    db_fields = repo.list_all()
    patient_fields = [
        {
            "field_name": f.field_name,
            "label": f.label,
            "field_type": f.field_type,
        }
        for f in db_fields
    ]

    return svc.chat(
        message=req.message,
        patient_fields=patient_fields if patient_fields else None,
        attachments=[
            {"filename": a.filename, "content": a.content}
            for a in req.attachments
        ] if req.attachments else None,
    )




