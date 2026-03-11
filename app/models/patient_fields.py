"""Patient fields ORM model."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.infra.db import Base


class PatientFieldModel(Base):
    """Patient fields table mapping."""

    __tablename__ = "patient_fields"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    field_name = Column(String(100), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=True)
    field_type = Column(String(50), nullable=False, default="float")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
