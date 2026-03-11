"""Formulas ORM model."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.infra.db import Base


class FormulaModel(Base):
    """Formulas table mapping."""

    __tablename__ = "formulas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    department_id = Column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    abbreviation = Column(String(50), nullable=True, comment="公式縮寫")
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    yaml_content = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

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

    department = relationship("DepartmentModel", back_populates="formulas")
    creator = relationship("UserModel", foreign_keys=[created_by])
    reviewer = relationship("UserModel", foreign_keys=[reviewed_by])
