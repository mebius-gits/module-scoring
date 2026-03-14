"""Centralized ORM model imports for metadata registration."""

from app.models.ai_chat import AiChatMessageModel, AiChatSessionModel
from app.models.departments import DepartmentModel
from app.models.formulas import FormulaModel
from app.models.items import ItemModel
from app.models.patient_fields import PatientFieldModel
from app.models.users import UserModel


def load_all_models() -> None:
    """Import all ORM models so Base.metadata is fully populated."""


__all__ = [
    "AiChatMessageModel",
    "AiChatSessionModel",
    "DepartmentModel",
    "FormulaModel",
    "ItemModel",
    "PatientFieldModel",
    "UserModel",
    "load_all_models",
]
