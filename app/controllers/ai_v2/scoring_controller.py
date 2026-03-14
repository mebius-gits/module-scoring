"""AI chat v2 controller with server-side memory."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.auth import require_role
from app.infra.clients.gemini_client import GeminiClient
from app.infra.db import get_db
from app.repositories.ai_chat_repo import AiChatMessageRepo, AiChatSessionRepo
from app.repositories.formula_repo import FormulaRepo
from app.repositories.patient_field_repo import PatientFieldRepo
from app.repositories.user_repo import UserModel
from app.schema.scoring import ChatV2Request, ChatV2Response
from app.services.ai.scoring_service import ScoringService

router = APIRouter(prefix="/v2/ai", tags=["AI Chat V2"])


def get_scoring_service(db: Session = Depends(get_db)) -> ScoringService:
    """Build the scoring service dependency for AI chat v2."""
    return ScoringService(
        formula_repo=FormulaRepo(db),
        gemini_client=GeminiClient(),
        patient_field_repo=PatientFieldRepo(db),
        ai_chat_session_repo=AiChatSessionRepo(db),
        ai_chat_message_repo=AiChatMessageRepo(db),
    )


@router.post(
    "/chat",
    response_model=ChatV2Response,
    summary="AI chat v2 with memory and YAML revision support",
)
def chat_v2(
    req: ChatV2Request,
    current_user: UserModel = require_role("admin", "reviewer", "builder"),
    db: Session = Depends(get_db),
    svc: ScoringService = Depends(get_scoring_service),
):
    """Run AI chat using persisted session memory."""
    db_fields = PatientFieldRepo(db).list_all()
    patient_fields = [
        {
            "field_name": f.field_name,
            "label": f.label,
            "field_type": f.field_type,
        }
        for f in db_fields
    ]

    return svc.chat_v2(
        user_id=current_user.id,
        session_id=req.session_id,
        message=req.message,
        yaml_content=req.yaml_content,
        memory_window=req.memory_window,
        patient_fields=patient_fields if patient_fields else None,
        attachments=[
            {"filename": a.filename, "content": a.content}
            for a in req.attachments
        ]
        if req.attachments
        else None,
    )
