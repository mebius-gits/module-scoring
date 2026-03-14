"""Repositories for persisted AI chat sessions and messages."""
import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.ai_chat import AiChatMessageModel, AiChatSessionModel


class AiChatSessionRepo:
    """Chat session repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, title: str | None = None) -> AiChatSessionModel:
        session = AiChatSessionModel(user_id=user_id, title=title)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: int) -> Optional[AiChatSessionModel]:
        return (
            self.db.query(AiChatSessionModel)
            .filter(AiChatSessionModel.id == session_id)
            .first()
        )

    def get_by_id_for_user(
        self, session_id: int, user_id: int
    ) -> Optional[AiChatSessionModel]:
        return (
            self.db.query(AiChatSessionModel)
            .filter(
                AiChatSessionModel.id == session_id,
                AiChatSessionModel.user_id == user_id,
            )
            .first()
        )

    def touch(self, session_id: int) -> Optional[AiChatSessionModel]:
        session = self.get_by_id(session_id)
        if session is None:
            return None
        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(session)
        return session

    def set_current_yaml(
        self, session_id: int, yaml_content: str | None
    ) -> Optional[AiChatSessionModel]:
        session = self.get_by_id(session_id)
        if session is None:
            return None
        session.current_yaml = yaml_content
        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(session)
        return session


class AiChatMessageRepo:
    """Chat message repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        session_id: int,
        role: str,
        content: str,
        attachments: list[dict] | None = None,
        formula_description: str | None = None,
        generated_yaml: str | None = None,
    ) -> AiChatMessageModel:
        message = AiChatMessageModel(
            session_id=session_id,
            role=role,
            message=content,
            attachments_json=json.dumps(attachments or [], ensure_ascii=False),
            formula_description=formula_description,
            generated_yaml=generated_yaml,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_recent_by_session(
        self, session_id: int, limit: int = 10
    ) -> List[AiChatMessageModel]:
        query = (
            self.db.query(AiChatMessageModel)
            .filter(AiChatMessageModel.session_id == session_id)
            .order_by(AiChatMessageModel.id.desc())
        )
        if limit > 0:
            query = query.limit(limit)
        return list(reversed(query.all()))

    def get_last_generated_yaml(
        self, session_id: int
    ) -> Optional[AiChatMessageModel]:
        return (
            self.db.query(AiChatMessageModel)
            .filter(
                AiChatMessageModel.session_id == session_id,
                AiChatMessageModel.generated_yaml.isnot(None),
            )
            .order_by(AiChatMessageModel.id.desc())
            .first()
        )
