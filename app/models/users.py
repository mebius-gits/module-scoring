"""
Users 相關的 Pydantic Schemas（Request / Response）。
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    admin = "admin"
    reviewer = "reviewer"
    builder = "builder"
    user = "user"


class UserCreate(BaseModel):
    """註冊請求"""
    username: str = Field(..., min_length=3, max_length=50, description="帳號")
    password: str = Field(..., min_length=6, max_length=128, description="密碼")
    display_name: Optional[str] = Field(None, max_length=100, description="顯示名稱")


class UserLogin(BaseModel):
    """登入請求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """使用者回應"""
    id: int
    username: str
    display_name: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT Token 回應"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
