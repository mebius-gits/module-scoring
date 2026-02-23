"""
DB 模組：封裝 SQLAlchemy Engine 與 Session 工廠。
支援 PostgreSQL / MySQL / SQLite，URL 以 settings.DB_URL 決定。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.infra.settings import settings

# connect_args 僅用於 SQLite（多執行緒設定）
_connect_args = {"check_same_thread": False} if settings.DB_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DB_URL,
    echo=False,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """所有 ORM Model 的基底類別"""
    pass


def get_db():
    """FastAPI Dependency：提供一個 DB Session，請求完畢後自動關閉"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
