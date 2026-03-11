"""
Departments 相關的 Pydantic Schemas（Request / Response）。
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    """建立 Department 的請求 Body"""
    name: str = Field(..., min_length=1, max_length=255, description="科別名稱")
    description: Optional[str] = Field(None, max_length=500, description="科別描述（選填）")


class DepartmentUpdate(BaseModel):
    """更新 Department 的請求 Body（全部欄位均為選填）"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


class DepartmentResponse(BaseModel):
    """Department 回應 Schema（不含公式列表）"""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FormulaInDepartment(BaseModel):
    """列出科別時顯示的輕量 formula 資訊"""
    id: int
    abbreviation: Optional[str] = None
    name: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DepartmentDetailResponse(BaseModel):
    """Department 詳細回應 Schema（含公式列表）"""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    formulas: List[FormulaInDepartment] = []

    model_config = {"from_attributes": True}
