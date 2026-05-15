from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "psychologist", name="userrole"),
            nullable=False,
            server_default="user",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"])

    # --- psychologists ---
    op.create_table(
        "psychologists",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bio", sa.Text()),
        sa.Column("specialization", sa.String(255)),
        sa.Column("price_per_hour", sa.Integer()),
    )
    op.create_index("ix_psychologists_id", "psychologists", ["id"])

    # --- schedule_slots ---
    op.create_table(
        "schedule_slots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("psychologist_id", sa.Integer(), sa.ForeignKey("psychologists.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_schedule_slots_id", "schedule_slots", ["id"])

    # --- appointments ---
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("psychologist_id", sa.Integer(), sa.ForeignKey("psychologists.id"), nullable=False),
        sa.Column("slot_id", sa.Integer(), sa.ForeignKey("schedule_slots.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "confirmed", "cancelled", "completed",
                name="appointmentstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("slot_id", name="uq_appointments_slot_id"),
    )
    op.create_index("ix_appointments_id", "appointments", ["id"])

    # --- video_sessions ---
    op.create_table(
        "video_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=False),
        sa.Column("room_id", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("ended_at", sa.DateTime()),
        sa.UniqueConstraint("appointment_id", name="uq_video_sessions_appointment_id"),
        sa.UniqueConstraint("room_id", name="uq_video_sessions_room_id"),
    )
    op.create_index("ix_video_sessions_id", "video_sessions", ["id"])


def downgrade() -> None:
    op.drop_table("video_sessions")
    op.drop_table("appointments")
    op.drop_table("schedule_slots")
    op.drop_table("psychologists")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS appointmentstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
