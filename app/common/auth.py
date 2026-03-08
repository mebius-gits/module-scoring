"""
認證與授權模組：JWT Token 處理、密碼雜湊、FastAPI 依賴注入。
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenException, UnauthorizedException
from app.infra.db import get_db
from app.infra.settings import settings
from app.repositories.user_repo import UserModel, UserRepo

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    """解析 JWT Token 並回傳目前登入的使用者"""
    if credentials is None:
        raise UnauthorizedException("缺少或無效的 Authorization Header")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (JWTError, ValueError, TypeError, KeyError):
        raise UnauthorizedException("Token 無效或已過期")
    user = UserRepo(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedException("使用者不存在或已停用")
    return user


def require_role(*allowed_roles: str):
    """
    產生角色檢查的 FastAPI Depends。
    用法：current_user: UserModel = require_role("admin", "builder")
    """
    def _dependency(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role not in allowed_roles:
            raise ForbiddenException(f"權限不足，需要角色: {', '.join(allowed_roles)}")
        return current_user
    return Depends(_dependency)
