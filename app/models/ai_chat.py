"""AI chat session/message ORM models."""
import json
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.infra.db import Base


class AiChatSessionModel(Base):
    """Persisted AI chat session used for server-side memory."""

    __tablename__ = "ai_chat_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=True)
    current_yaml = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("UserModel")
    messages = relationship(
        "AiChatMessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AiChatMessageModel.id",
    )


class AiChatMessageModel(Base):
    """Persisted AI chat message with optional generated YAML payload."""

    __tablename__ = "ai_chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(
        Integer,
        ForeignKey("ai_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    attachments_json = Column(Text, nullable=True)
    formula_description = Column(Text, nullable=True)
    generated_yaml = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("AiChatSessionModel", back_populates="messages")

    @property
    def content(self) -> str:
        return self.message

    @content.setter
    def content(self, value: str) -> None:
        self.message = value

    @property
    def attachments(self) -> list[dict]:
        if not self.attachments_json:
            return []
        try:
            data = json.loads(self.attachments_json)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    @attachments.setter
    def attachments(self, value: list[dict] | None) -> None:
        self.attachments_json = json.dumps(value or [], ensure_ascii=False)
