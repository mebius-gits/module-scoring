"""Items ORM model."""
from sqlalchemy import Column, Integer, String

from app.infra.db import Base


class ItemModel(Base):
    """Items table mapping."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
