"""
Item Repository：封裝 Items 的 SQLAlchemy ORM Model 與資料存取操作。
商業邏輯一律不在此層，Repository 只負責 CRUD。
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.items import ItemModel
from app.schema.items import ItemCreate, ItemUpdate


class ItemRepo:
    """
    Item 資料存取物件 (DAO)。
    透過 FastAPI Dependency Injection 注入 db Session。
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, item_in: ItemCreate) -> ItemModel:
        db_item = ItemModel(**item_in.model_dump())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def list_all(self, skip: int = 0, limit: int = 100) -> List[ItemModel]:
        return self.db.query(ItemModel).offset(skip).limit(limit).all()

    def get_by_id(self, item_id: int) -> Optional[ItemModel]:
        return self.db.query(ItemModel).filter(ItemModel.id == item_id).first()

    def update(self, item_id: int, item_in: ItemUpdate) -> Optional[ItemModel]:
        db_item = self.get_by_id(item_id)
        if db_item is None:
            return None
        for field, value in item_in.model_dump(exclude_none=True).items():
            setattr(db_item, field, value)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def delete(self, item_id: int) -> bool:
        db_item = self.get_by_id(item_id)
        if db_item is None:
            return False
        self.db.delete(db_item)
        self.db.commit()
        return True
