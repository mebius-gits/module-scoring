"""
Auth Service：封裝使用者註冊、登入的商業邏輯。
"""
from app.common.auth import create_access_token, hash_password, verify_password
from app.common.exceptions import UnauthorizedException, ValidationException
from app.models.users import UserCreate, UserResponse, TokenResponse
from app.repositories.user_repo import UserRepo


class AuthService:
    """認證商業邏輯層"""

    def __init__(self, repo: UserRepo):
        self.repo = repo

    def register(self, data: UserCreate) -> UserResponse:
        existing = self.repo.get_by_username(data.username)
        if existing:
            raise ValidationException(f"使用者名稱 '{data.username}' 已被使用")
        # 第一位註冊的使用者自動成為 admin
        role = "admin" if self.repo.count() == 0 else "user"
        hashed = hash_password(data.password)
        user = self.repo.create(data.username, hashed, data.display_name, role)
        return UserResponse.model_validate(user)

    def login(self, username: str, password: str) -> TokenResponse:
        user = self.repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedException("帳號或密碼錯誤")
        if not user.is_active:
            raise UnauthorizedException("此帳號已停用")
        token = create_access_token(user.id, user.role)
        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )
