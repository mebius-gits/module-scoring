"""
PatientField Repository：封裝 PatientFields 的 SQLAlchemy ORM Model 與資料存取操作。
病人欄位名稱登錄（僅存中繼資料，不含實際病人資料）。
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.patient_fields import PatientFieldModel
from app.schema.patient_fields import PatientFieldCreate, PatientFieldUpdate


class PatientFieldRepo:
    """PatientField 資料存取物件 (DAO)"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: PatientFieldCreate) -> PatientFieldModel:
        field = PatientFieldModel(
            field_name=data.field_name.strip(),
            label=data.label,
            field_type=data.field_type,
        )
        self.db.add(field)
        self.db.commit()
        self.db.refresh(field)
        return field

    def list_all(self) -> List[PatientFieldModel]:
        return self.db.query(PatientFieldModel).order_by(PatientFieldModel.id).all()

    def get_by_id(self, field_id: int) -> Optional[PatientFieldModel]:
        return self.db.query(PatientFieldModel).filter(
            PatientFieldModel.id == field_id
        ).first()

    def update(self, field_id: int, data: PatientFieldUpdate) -> Optional[PatientFieldModel]:
        field = self.get_by_id(field_id)
        if field is None:
            return None
        for attr, value in data.model_dump(exclude_none=True).items():
            setattr(field, attr, value)
        self.db.commit()
        self.db.refresh(field)
        return field

    def delete(self, field_id: int) -> bool:
        field = self.get_by_id(field_id)
        if field is None:
            return False
        self.db.delete(field)
        self.db.commit()
        return True

    def count(self) -> int:
        """回傳目前 PatientField 總數"""
        return self.db.query(PatientFieldModel).count()
