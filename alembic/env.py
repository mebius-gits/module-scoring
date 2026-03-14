"""
Alembic migration env.py
自動讀取 app/infra/settings.py 的 DATABASE_URL，無需在 alembic.ini 硬寫連線字串。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 讀取 alembic.ini 的 logging 設定
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 讀取 app settings 並覆蓋 sqlalchemy.url
from app.infra.settings import settings
from app.infra.db import Base
from app.models import load_all_models

load_all_models()

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
IGNORED_TABLES = {"ai_chat_messages", "ai_chat_sessions"}


def include_object(object_, name, type_, reflected, compare_to):
    """Ignore unmanaged tables that live in the same database."""
    if type_ == "table" and name in IGNORED_TABLES:
        return False
    return True


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
        render_as_batch=_is_sqlite(url),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
