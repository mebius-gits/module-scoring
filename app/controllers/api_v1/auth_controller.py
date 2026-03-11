"""
/api/v1/auth Controller：使用者註冊、登入、查看個人資訊。
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.auth import get_current_user, require_role
from app.infra.db import get_db
from app.schema.users import UpdateUserRole, UserCreate, UserLogin, UserResponse, TokenResponse
from app.repositories.user_repo import UserModel, UserRepo
from app.services.auth_service import AuthService

router = APIRouter(prefix="/v1/auth", tags=["Auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepo(db))


@router.post("/register", response_model=UserResponse, status_code=201, summary="註冊帳號")
def register(
    data: UserCreate,
    svc: AuthService = Depends(get_auth_service),
):
    """第一位註冊者自動成為 admin，後續註冊者預設為 user 角色。"""
    return svc.register(data)


@router.post("/login", response_model=TokenResponse, summary="登入取得 Token")
def login(
    data: UserLogin,
    svc: AuthService = Depends(get_auth_service),
):
    return svc.login(data.username, data.password)


@router.get("/me", response_model=UserResponse, summary="查看目前登入者資訊")
def get_me(
    current_user: UserModel = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)


# ─── Admin 使用者管理 ───────────────────────────────────────


@router.get("/users", response_model=List[UserResponse], summary="列出所有使用者（Admin）")
def list_users(
    _: UserModel = require_role("admin"),
    svc: AuthService = Depends(get_auth_service),
):
    return svc.list_users()


@router.patch("/users/{user_id}/role", response_model=UserResponse, summary="修改使用者角色（Admin）")
def update_user_role(
    user_id: int,
    body: UpdateUserRole,
    _: UserModel = require_role("admin"),
    svc: AuthService = Depends(get_auth_service),
):
    return svc.update_role(user_id, body.role.value)
