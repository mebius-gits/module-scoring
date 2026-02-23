"""
Alembic migration env.py
自動讀取 app/infra/settings.py 的 DB_URL，無需在 alembic.ini 硬寫連線字串。
"""
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
# 匯入所有 ORM Model 讓 autogenerate 可偵測
from app.repositories.item_repo import ItemModel  # noqa: F401

config.set_main_option("sqlalchemy.url", settings.DB_URL)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
