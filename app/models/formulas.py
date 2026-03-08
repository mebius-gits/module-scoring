"""
Formulas 相關的 Pydantic Schemas（Request / Response）。
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FormulaStatus(str, Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"


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
    is_active: bool = True
    status: FormulaStatus = FormulaStatus.draft
    created_by: Optional[int] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReviewAction(BaseModel):
    """審核動作請求（核准/駁回）"""
    comment: Optional[str] = Field(None, max_length=1000, description="審核意見")
