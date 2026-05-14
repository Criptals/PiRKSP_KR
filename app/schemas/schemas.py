from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.models import AppointmentStatus, UserRole


class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=6, max_length=255)
    role: UserRole = UserRole.user

    @field_validator("full_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Имя не должно быть пустым")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    password: str | None = Field(default=None, min_length=6)


class PsychologistProfileUpdate(BaseModel):
    bio: str | None = None
    specialization: str | None = Field(default=None, max_length=255)
    price_per_hour: int | None = Field(default=None, ge=0)


class PsychologistOut(BaseModel):
    id: int
    user_id: int
    bio: str | None
    specialization: str | None
    price_per_hour: int | None
    user: UserOut

    model_config = {"from_attributes": True}


class SlotCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime

    @field_validator("ends_at")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("starts_at")
        if start and v <= start:
            raise ValueError("Конец слота должен быть позже начала")
        return v


class SlotOut(BaseModel):
    id: int
    psychologist_id: int
    starts_at: datetime
    ends_at: datetime
    is_available: bool

    model_config = {"from_attributes": True}


class AppointmentCreate(BaseModel):
    slot_id: int
    notes: str | None = Field(default=None, max_length=1000)


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class AppointmentOut(BaseModel):
    id: int
    patient_id: int
    psychologist_id: int
    slot_id: int
    status: AppointmentStatus
    notes: str | None
    created_at: datetime
    slot: SlotOut

    model_config = {"from_attributes": True}


class VideoSessionOut(BaseModel):
    id: int
    appointment_id: int
    room_id: str
    is_active: bool
    started_at: datetime | None
    ended_at: datetime | None

    model_config = {"from_attributes": True}
