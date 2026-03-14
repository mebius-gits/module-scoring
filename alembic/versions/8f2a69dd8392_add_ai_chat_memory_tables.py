"""add_ai_chat_memory_tables

Revision ID: 8f2a69dd8392
Revises: 69e070b69cba
Create Date: 2026-03-14 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "8f2a69dd8392"
down_revision: Union[str, None] = "69e070b69cba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("ai_chat_sessions"):
        op.create_table(
            "ai_chat_sessions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("current_yaml", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        session_columns = {
            column["name"] for column in inspector.get_columns("ai_chat_sessions")
        }
        if "current_yaml" not in session_columns:
            op.add_column(
                "ai_chat_sessions",
                sa.Column("current_yaml", sa.Text(), nullable=True),
            )

    session_indexes = {
        index["name"] for index in inspector.get_indexes("ai_chat_sessions")
    }
    if op.f("ix_ai_chat_sessions_user_id") not in session_indexes:
        op.create_index(
            op.f("ix_ai_chat_sessions_user_id"),
            "ai_chat_sessions",
            ["user_id"],
            unique=False,
        )

    if not inspector.has_table("ai_chat_messages"):
        op.create_table(
            "ai_chat_messages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("attachments_json", sa.Text(), nullable=True),
            sa.Column("formula_description", sa.Text(), nullable=True),
            sa.Column("generated_yaml", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["session_id"], ["ai_chat_sessions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        message_columns = {
            column["name"] for column in inspector.get_columns("ai_chat_messages")
        }
        if "message" not in message_columns and "content" in message_columns:
            op.add_column(
                "ai_chat_messages",
                sa.Column("message", sa.Text(), nullable=True),
            )
            op.execute(sa.text("UPDATE ai_chat_messages SET message = content"))
            with op.batch_alter_table("ai_chat_messages") as batch_op:
                batch_op.alter_column("message", existing_type=sa.Text(), nullable=False)
        if "attachments_json" not in message_columns:
            op.add_column(
                "ai_chat_messages",
                sa.Column("attachments_json", sa.Text(), nullable=True),
            )

    message_indexes = {
        index["name"] for index in inspector.get_indexes("ai_chat_messages")
    }
    if op.f("ix_ai_chat_messages_id") not in message_indexes:
        op.create_index(
            op.f("ix_ai_chat_messages_id"),
            "ai_chat_messages",
            ["id"],
            unique=False,
        )
    if op.f("ix_ai_chat_messages_session_id") not in message_indexes:
        op.create_index(
            op.f("ix_ai_chat_messages_session_id"),
            "ai_chat_messages",
            ["session_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_chat_messages_session_id"), table_name="ai_chat_messages")
    op.drop_index(op.f("ix_ai_chat_messages_id"), table_name="ai_chat_messages")
    op.drop_table("ai_chat_messages")

    op.drop_index(op.f("ix_ai_chat_sessions_user_id"), table_name="ai_chat_sessions")
    op.drop_index(op.f("ix_ai_chat_sessions_id"), table_name="ai_chat_sessions")
    op.drop_table("ai_chat_sessions")
