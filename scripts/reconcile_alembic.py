"""Verify the current schema and optionally stamp it to Alembic head."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infra.settings import settings
from app.models import load_all_models

load_all_models()

EXPECTED_TABLES = {
    "departments": {
        "id",
        "name",
        "description",
        "created_at",
        "updated_at",
        "is_active",
    },
    "formulas": {
        "id",
        "department_id",
        "abbreviation",
        "name",
        "description",
        "yaml_content",
        "created_at",
        "updated_at",
        "is_active",
        "status",
        "created_by",
        "reviewed_by",
        "reviewed_at",
        "review_comment",
    },
    "items": {"id", "name", "description"},
    "patient_fields": {"id", "field_name", "label", "field_type", "created_at"},
    "users": {
        "id",
        "username",
        "password_hash",
        "display_name",
        "role",
        "is_active",
        "created_at",
        "updated_at",
    },
}


def _inspect_schema() -> tuple[list[str], dict[str, list[str]], str | None]:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        inspector = inspect(conn)
        missing_tables: list[str] = []
        missing_columns: dict[str, list[str]] = {}

        for table_name, expected_columns in EXPECTED_TABLES.items():
            if not inspector.has_table(table_name):
                missing_tables.append(table_name)
                continue

            actual_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            missing = sorted(expected_columns - actual_columns)
            if missing:
                missing_columns[table_name] = missing

        version = None
        if inspector.has_table("alembic_version"):
            version = conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).scalar_one_or_none()

    return missing_tables, missing_columns, version


def _build_alembic_config() -> Config:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    return config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check whether the current DB can be stamped to Alembic head."
    )
    parser.add_argument(
        "--stamp-head",
        action="store_true",
        help="Stamp the current schema as Alembic head after compatibility checks.",
    )
    args = parser.parse_args()

    missing_tables, missing_columns, version = _inspect_schema()

    if missing_tables or missing_columns:
        print("Schema does not match the managed application tables.")
        if missing_tables:
            print(f"Missing tables: {', '.join(missing_tables)}")
        for table_name, columns in missing_columns.items():
            print(f"Missing columns in {table_name}: {', '.join(columns)}")
        return 1

    if version:
        print(f"Alembic is already tracking this DB at revision: {version}")
        return 0

    print("Schema matches the current application tables.")
    if not args.stamp_head:
        print("Run with --stamp-head to record the current schema in alembic_version.")
        return 0

    command.stamp(_build_alembic_config(), "head")
    print("Stamped current schema to Alembic head.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
