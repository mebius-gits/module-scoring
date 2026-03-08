"""
/api/v1/auth Controller：使用者註冊、登入、查看個人資訊。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.auth import get_current_user
from app.infra.db import get_db
from app.models.users import UserCreate, UserLogin, UserResponse, TokenResponse
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
