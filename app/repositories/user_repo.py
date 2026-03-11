"""User Repository：封裝 Users 的資料存取操作。"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.users import UserModel


class UserRepo:
    """User 資料存取物件 (DAO)"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.username == username).first()

    def get_by_id(self, user_id: int) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

    def create(
        self,
        username: str,
        password_hash: str,
        display_name: Optional[str] = None,
        role: str = "user",
    ) -> UserModel:
        user = UserModel(
            username=username,
            password_hash=password_hash,
            display_name=display_name,
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def count(self) -> int:
        return self.db.query(UserModel).count()

    def list_all(self) -> list[UserModel]:
        return self.db.query(UserModel).order_by(UserModel.id).all()

    def update_role(self, user_id: int, role: str) -> Optional[UserModel]:
        user = self.get_by_id(user_id)
        if user is None:
            return None
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user
