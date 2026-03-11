"""
/api/v2/items Controller：v2 版本 HTTP 路由定義，處理 request/response，不含商業邏輯。
以 FastAPI Dependency Injection 注入 ItemService，捕捉 Domain 例外並轉換 HTTP status。
"""
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.auth import get_current_user
from app.infra.db import get_db
from app.schema.items import ItemCreate, ItemResponse, ItemUpdate
from app.repositories.item_repo import ItemRepo
from app.repositories.user_repo import UserModel
from app.services.item_service import ItemService

router = APIRouter(prefix="/v2/items", tags=["Items V2"])


def get_item_service(db: Session = Depends(get_db)) -> ItemService:
    """建立 ItemService 並注入 DB Session"""
    return ItemService(ItemRepo(db))


@router.post("", response_model=ItemResponse, status_code=201, summary="建立商品")
def create_item(
    item: ItemCreate,
    current_user: UserModel = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
):
    return svc.create_item(item)


@router.get("", response_model=List[ItemResponse], summary="列出所有商品")
def list_items(
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(100, ge=1, le=500, description="最多回傳筆數"),
    current_user: UserModel = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
):
    return svc.list_items(skip=skip, limit=limit)


@router.get("/{item_id}", response_model=ItemResponse, summary="取得單一商品")
def get_item(
    item_id: int,
    current_user: UserModel = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
):
    return svc.get_item(item_id)


@router.put("/{item_id}", response_model=ItemResponse, summary="更新商品")
def update_item(
    item_id: int,
    item: ItemUpdate,
    current_user: UserModel = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
):
    return svc.update_item(item_id, item)


@router.delete("/{item_id}", status_code=204, summary="刪除商品")
def delete_item(
    item_id: int,
    current_user: UserModel = Depends(get_current_user),
    svc: ItemService = Depends(get_item_service),
):
    svc.delete_item(item_id)
