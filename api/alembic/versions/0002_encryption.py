"""Encryption: sensitive fields become ciphertext + nonce, and the DEK/KEK keyring is added.

This migration runs on the orienta_encrypted database, which starts empty. It refuses to run
on a database that already holds users, because plain-text values would be lost.

Revision ID: 0002
Revises: 0001
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

kek_status = postgresql.ENUM("ACTIVE", "RETIRED", name="kek_status", create_type=False)
user_key_status = postgresql.ENUM("ACTIVE", "DESTROYED", name="user_key_status", create_type=False)
encryption_mode = postgresql.ENUM("ENCRYPTED", "PLAINTEXT", name="encryption_mode", create_type=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT count(*) FROM users")).scalar():
        raise RuntimeError("Migration 0002 needs an empty database: use the orienta_encrypted database (see README).")

    for enum in (kek_status, user_key_status, encryption_mode):
        enum.create(bind, checkfirst=True)

    # ---- keyring ----
    op.create_table(
        "key_encryption_keys",
        *_timestamps(),
        sa.Column("version", sa.Integer(), nullable=False, unique=True),
        sa.Column("status", kek_status, nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
    )
    op.create_index("uq_key_encryption_keys_active", "key_encryption_keys", ["status"], unique=True,
                    postgresql_where=sa.text("status = 'ACTIVE'"))
    # Version 1 is active from the start; the key itself is the KEK_V1 environment variable.
    op.execute(sa.text("INSERT INTO key_encryption_keys (id, version, status) VALUES (:id, 1, 'ACTIVE')").bindparams(id=uuid.uuid4()))

    op.create_table(
        "user_keys",
        *_timestamps(),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("kek_id", sa.Uuid(), sa.ForeignKey("key_encryption_keys.id"), nullable=False, index=True),
        sa.Column("wrapped_dek", sa.LargeBinary()),
        sa.Column("wrapped_dek_nonce", sa.LargeBinary()),
        sa.Column("status", user_key_status, nullable=False),
        sa.Column("destroyed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status = 'ACTIVE' OR wrapped_dek IS NULL", name="ck_user_keys_destroyed"),
    )

    # ---- users: e-mail, name and phone are encrypted; e-mail and phone get a blind index ----
    op.drop_constraint("users_email_key", "users", type_="unique")
    for column in ("email", "full_name", "phone"):
        op.drop_column("users", column)
    for column, nullable in (("email_ciphertext", False), ("email_nonce", False), ("email_blind_index", False),
                             ("full_name_ciphertext", False), ("full_name_nonce", False),
                             ("phone_ciphertext", True), ("phone_nonce", True), ("phone_blind_index", True)):
        op.add_column("users", sa.Column(column, sa.LargeBinary(), nullable=nullable))
    op.create_unique_constraint("uq_users_email_blind_index", "users", ["email_blind_index"])
    op.create_index("uq_users_phone_blind_index", "users", ["phone_blind_index"], unique=True,
                    postgresql_where=sa.text("phone_blind_index IS NOT NULL"))

    # ---- messages: ciphertext + nonce, plain text only in the PLAINTEXT demo mode ----
    op.drop_column("messages", "content")
    op.add_column("messages", sa.Column("encryption_mode", encryption_mode, nullable=False, server_default="ENCRYPTED"))
    op.add_column("messages", sa.Column("content_ciphertext", sa.LargeBinary()))
    op.add_column("messages", sa.Column("content_nonce", sa.LargeBinary()))
    op.add_column("messages", sa.Column("content_plaintext", sa.Text()))
    op.create_check_constraint(
        "ck_messages_encryption_mode", "messages",
        "(encryption_mode = 'ENCRYPTED' AND content_ciphertext IS NOT NULL AND content_nonce IS NOT NULL AND content_plaintext IS NULL)"
        " OR (encryption_mode = 'PLAINTEXT' AND content_plaintext IS NOT NULL AND content_ciphertext IS NULL)",
    )

    # ---- agent notes ----
    op.drop_column("callback_requests", "outcome_note")
    op.add_column("callback_requests", sa.Column("outcome_note_ciphertext", sa.LargeBinary()))
    op.add_column("callback_requests", sa.Column("outcome_note_nonce", sa.LargeBinary()))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT count(*) FROM users")).scalar():
        raise RuntimeError("Downgrade 0002 needs an empty database: encrypted values cannot be turned back into plain text.")

    op.drop_column("callback_requests", "outcome_note_nonce")
    op.drop_column("callback_requests", "outcome_note_ciphertext")
    op.add_column("callback_requests", sa.Column("outcome_note", sa.Text()))

    op.drop_constraint("ck_messages_encryption_mode", "messages", type_="check")
    for column in ("content_plaintext", "content_nonce", "content_ciphertext", "encryption_mode"):
        op.drop_column("messages", column)
    op.add_column("messages", sa.Column("content", sa.Text(), nullable=False))

    op.drop_index("uq_users_phone_blind_index", table_name="users")
    op.drop_constraint("uq_users_email_blind_index", "users", type_="unique")
    for column in ("phone_blind_index", "phone_nonce", "phone_ciphertext", "full_name_nonce", "full_name_ciphertext",
                   "email_blind_index", "email_nonce", "email_ciphertext"):
        op.drop_column("users", column)
    op.add_column("users", sa.Column("email", sa.String(320), nullable=False))
    op.add_column("users", sa.Column("full_name", sa.String(200), nullable=False))
    op.add_column("users", sa.Column("phone", sa.String(32)))
    op.create_unique_constraint("users_email_key", "users", ["email"])

    op.drop_table("user_keys")
    op.drop_index("uq_key_encryption_keys_active", table_name="key_encryption_keys")
    op.drop_table("key_encryption_keys")
    for enum in (encryption_mode, user_key_status, kek_status):
        enum.drop(bind, checkfirst=True)
