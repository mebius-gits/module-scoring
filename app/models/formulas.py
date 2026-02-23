"""
Formulas 相關的 Pydantic Schemas（Request / Response）。
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FormulaCreate(BaseModel):
    """建立 Formula 的請求 Body"""
    name: str = Field(..., min_length=1, max_length=255, description="公式名稱")
    description: Optional[str] = Field(None, max_length=500, description="公式描述（選填）")
    ast_data: Dict[str, Any] = Field(..., description="AST JSON 資料")
    yaml_content: str = Field(..., description="YAML 公式字串")


class FormulaUpdate(BaseModel):
    """更新 Formula 的請求 Body（全部欄位均為選填）"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    ast_data: Optional[Dict[str, Any]] = None
    yaml_content: Optional[str] = None


class FormulaResponse(BaseModel):
    """Formula 回應 Schema"""
    id: int
    department_id: int
    name: str
    description: Optional[str] = None
    ast_data: Dict[str, Any]
    yaml_content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
