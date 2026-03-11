"""
Item Service：封裝 Item 的商業邏輯與用例流程。
協調 ItemRepo 進行資料存取，回傳 Pydantic Schema，不回傳 ORM 物件。
"""
from typing import List
from sqlalchemy.orm import Session

from app.schema.items import ItemCreate, ItemResponse, ItemUpdate
from app.repositories.item_repo import ItemRepo
from app.common.exceptions import NotFoundException


class ItemService:
    """
    Item 商業邏輯層。
    由 Controller 透過 Dependency Injection 注入。
    """

    def __init__(self, repo: ItemRepo):
        self.repo = repo

    def create_item(self, item_in: ItemCreate) -> ItemResponse:
        """建立新 Item，回傳 Pydantic Response Schema"""
        db_item = self.repo.create(item_in)
        return ItemResponse.model_validate(db_item)

    def list_items(self, skip: int = 0, limit: int = 100) -> List[ItemResponse]:
        """列出所有 Items，支援分頁"""
        db_items = self.repo.list_all(skip=skip, limit=limit)
        return [ItemResponse.model_validate(i) for i in db_items]

    def get_item(self, item_id: int) -> ItemResponse:
        """依 ID 取得 Item；不存在時拋出 NotFoundException"""
        db_item = self.repo.get_by_id(item_id)
        if db_item is None:
            raise NotFoundException(f"Item {item_id} 不存在")
        return ItemResponse.model_validate(db_item)

    def update_item(self, item_id: int, item_in: ItemUpdate) -> ItemResponse:
        """更新 Item；不存在時拋出 NotFoundException"""
        db_item = self.repo.update(item_id, item_in)
        if db_item is None:
            raise NotFoundException(f"Item {item_id} 不存在")
        return ItemResponse.model_validate(db_item)

    def delete_item(self, item_id: int) -> None:
        """刪除 Item；不存在時拋出 NotFoundException"""
        success = self.repo.delete(item_id)
        if not success:
            raise NotFoundException(f"Item {item_id} 不存在")
