"""
Formulas 相關的 Pydantic Schemas（Request / Response）。
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class FormulaStatus(str, Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"


class FormulaCreate(BaseModel):
    """建立 Formula 的請求 Body"""
    abbreviation: Optional[str] = Field(None, max_length=50, description="公式縮寫（選填）")
    name: str = Field(..., min_length=1, max_length=255, description="公式名稱")
    description: Optional[str] = Field(None, max_length=500, description="公式描述（選填）")
    yaml_content: str = Field(..., description="YAML 公式字串")


class FormulaUpdate(BaseModel):
    """更新 Formula 的請求 Body（全部欄位均為選填）"""
    abbreviation: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    yaml_content: Optional[str] = None


class UserBrief(BaseModel):
    """精簡使用者資訊（嵌入用）"""
    id: int
    username: str
    display_name: Optional[str] = None

    model_config = {"from_attributes": True}


class FormulaResponse(BaseModel):
    """Formula 回應 Schema"""
    id: int
    department_id: int
    abbreviation: Optional[str] = None
    name: str
    description: Optional[str] = None
    yaml_content: str
    is_active: bool = True
    status: FormulaStatus = FormulaStatus.draft
    created_by: Optional[UserBrief] = None
    reviewed_by: Optional[UserBrief] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def _map_relationships(cls, data):
        """將 ORM relationship (creator/reviewer) 對應到 created_by/reviewed_by。"""
        if hasattr(data, "__dict__"):
            # ORM object
            obj = data
            d = {}
            for f in ["id", "department_id", "abbreviation", "name", "description",
                       "yaml_content", "is_active", "status", "reviewed_at",
                       "review_comment", "created_at", "updated_at"]:
                d[f] = getattr(obj, f, None)
            d["created_by"] = getattr(obj, "creator", None)
            d["reviewed_by"] = getattr(obj, "reviewer", None)
            return d
        return data

    model_config = {"from_attributes": True}


class ReviewAction(BaseModel):
    """審核動作請求（核准/駁回）"""
    comment: Optional[str] = Field(None, max_length=1000, description="審核意見")
