"""
Items 相關的 Pydantic Schemas（Request / Response）。
Service 回傳 ItemResponse，Controller 直接序列化給前端，避免 ORM 物件外洩。
"""
from typing import Optional
from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    """建立 Item 的請求 Body"""
    name: str = Field(..., min_length=1, max_length=100, description="商品名稱")
    description: Optional[str] = Field(None, max_length=500, description="商品描述（選填）")


class ItemUpdate(BaseModel):
    """更新 Item 的請求 Body（全部欄位均為選填）"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ItemResponse(BaseModel):
    """Item 回應 Schema"""
    id: int
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}
