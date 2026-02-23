"""
PatientFields 相關的 Pydantic Schemas（Request / Response）。
病人欄位名稱登錄，僅存欄位中繼資料（不含實際病人資料）。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PatientFieldCreate(BaseModel):
    """登錄新病人欄位"""
    field_name: str = Field(..., min_length=1, max_length=100, description="欄位名稱，如 height")
    label: Optional[str] = Field(None, max_length=255, description="顯示標籤，如 身高 (公尺)")
    field_type: str = Field("float", max_length=50, description="欄位型態：int / float / boolean / string")


class PatientFieldUpdate(BaseModel):
    """更新病人欄位（全部欄位均為選填）"""
    label: Optional[str] = Field(None, max_length=255)
    field_type: Optional[str] = Field(None, max_length=50)


class PatientFieldResponse(BaseModel):
    """PatientField 回應 Schema"""
    id: int
    field_name: str
    label: Optional[str] = None
    field_type: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
