import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class UserRole(str, enum.Enum):
    user = "user"
    psychologist = "psychologist"


class AppointmentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class User(Base):
    """Профиль пользователя"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    psychologist_profile: Mapped["Psychologist"] = relationship(
        "Psychologist", back_populates="user", uselist=False
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="patient", foreign_keys="Appointment.patient_id"
    )


class Psychologist(Base):
    """Расширенный профиль психолога — создаётся поверх записи User."""

    __tablename__ = "psychologists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    specialization: Mapped[str | None] = mapped_column(String(255))
    price_per_hour: Mapped[int | None] = mapped_column(Integer)

    user: Mapped[User] = relationship("User", back_populates="psychologist_profile")
    schedule_slots: Mapped[list["ScheduleSlot"]] = relationship(
        "ScheduleSlot", back_populates="psychologist", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="psychologist"
    )


class ScheduleSlot(Base):
    """Свободный слот в расписании психолога."""

    __tablename__ = "schedule_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    psychologist_id: Mapped[int] = mapped_column(ForeignKey("psychologists.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    psychologist: Mapped[Psychologist] = relationship("Psychologist", back_populates="schedule_slots")
    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="slot", uselist=False)


class Appointment(Base):
    """Запись пользователя к психологу на конкретный слот."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    psychologist_id: Mapped[int] = mapped_column(ForeignKey("psychologists.id"), nullable=False)
    slot_id: Mapped[int] = mapped_column(ForeignKey("schedule_slots.id"), unique=True, nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.pending
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    patient: Mapped[User] = relationship("User", back_populates="appointments", foreign_keys=[patient_id])
    psychologist: Mapped[Psychologist] = relationship("Psychologist", back_populates="appointments")
    slot: Mapped[ScheduleSlot] = relationship("ScheduleSlot", back_populates="appointment")
    session: Mapped["VideoSession"] = relationship(
        "VideoSession", back_populates="appointment", uselist=False
    )


class VideoSession(Base):
    """Видеосессия, привязанная к конкретной записи."""

    __tablename__ = "video_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id"), unique=True, nullable=False
    )
    room_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)

    appointment: Mapped[Appointment] = relationship("Appointment", back_populates="session")
