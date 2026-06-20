import random
from datetime import datetime
from enum import Enum
from typing import Optional

import pytest
from pydantic import BaseModel, Field, ValidationError, EmailStr, field_validator



class UserRole(str, Enum):
    user = "user"
    psychologist = "psychologist"

class AppointmentStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"

PG_INT4_MAX = 2_147_483_647


class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=6)
    role: UserRole = UserRole.user

    @field_validator("full_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Имя не должно быть пустым")
        return v.strip()

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

class PsychologistProfileUpdate(BaseModel):
    bio: str | None = None
    specialization: str | None = Field(default=None, max_length=255)
    price_per_hour: int | None = Field(default=None, ge=0)

class AppointmentCreate(BaseModel):
    slot_id: int = Field(gt=0, le=PG_INT4_MAX)
    notes: str | None = Field(default=None, max_length=1000)


def mutate_string(data: str, count: int = 5, max_len: int | None = None) -> list[str]:
    """Генерирует мутированные версии строки."""
    mutations = [data]
    weird_chars = '\x00\n\t\r\x0b\x0c\u202e\ufeff\u200b<>&;\'"\\/'

    for _ in range(count):
        if not data:
            mutated = random.choice(['', ' ', '\x00', 'A' * 100, '<script>'])
        else:
            lst = list(data)
            if max_len and len(lst) >= max_len:
                action = random.choice(['delete', 'replace', 'shuffle'])
            else:
                action = random.choice(['insert', 'delete', 'replace', 'shuffle'])

            if action == 'insert':
                idx = random.randint(0, len(lst))
                lst.insert(idx, random.choice(weird_chars))
            elif action == 'delete' and lst:
                lst.pop(random.randint(0, len(lst) - 1))
            elif action == 'replace' and lst:
                idx = random.randint(0, len(lst) - 1)
                lst[idx] = random.choice(weird_chars)
            elif action == 'shuffle' and len(lst) > 1:
                random.shuffle(lst)

            mutated = ''.join(lst)
        mutations.append(mutated)
    return mutations

def mutate_int(val: int, count: int = 5) -> list[int]:
    """Генерирует граничные значения для целых чисел."""
    candidates = [
        val, val + 1, val - 1,
        0, 1, -1,
        PG_INT4_MAX, PG_INT4_MAX + 1, PG_INT4_MAX - 1,
        -PG_INT4_MAX, -PG_INT4_MAX - 1,
        random.randint(-10**9, 10**9)
    ]
    return random.sample(candidates, min(count, len(candidates)))


class TestStandaloneFuzz:

    @pytest.mark.parametrize("base_name", ["", "A", "AB", "   ", "<script>", "A" * 300])
    def test_user_register_name(self, base_name):
        """Фаззинг имени пользователя."""
        candidates = mutate_string(base_name, 5)

        for name in candidates:
            try:
                u = UserRegister(
                    email="test@example.com",
                    full_name=name,
                    password="secure123",
                    role=UserRole.user
                )
                assert u.full_name.strip(), f"Accepted blank name: {repr(name)}"
            except ValidationError:
                pass
            except Exception as e:
                pytest.fail(f"Crash on name {repr(name)}: {type(e).__name__}: {e}")

    @pytest.mark.parametrize("base_pwd", ["12345", "secret", "", "a" * 1000])
    def test_user_register_password(self, base_pwd):
        """Фаззинг пароля."""
        candidates = mutate_string(base_pwd, 5)

        for pwd in candidates:
            try:
                u = UserRegister(
                    email="test@example.com",
                    full_name="Test User",
                    password=pwd,
                    role=UserRole.user
                )
                assert len(u.password) >= 6
            except ValidationError:
                pass
            except Exception as e:
                pytest.fail(f"Crash on password: {type(e).__name__}: {e}")

    @pytest.mark.parametrize("start, end", [
        (datetime(2024, 1, 1, 10, 0), datetime(2024, 1, 1, 9, 0)), # Invalid: end < start
        (datetime(2024, 1, 1, 10, 0), datetime(2024, 1, 1, 10, 0)), # Invalid: end == start
        (datetime(2024, 1, 1, 10, 0), datetime(2024, 1, 1, 10, 1)), # Valid
    ])
    def test_slot_create_dates(self, start, end):
        """Фаззинг дат слота."""
        try:
            s = SlotCreate(starts_at=start, ends_at=end)
            assert s.ends_at > s.starts_at, "Logic error: ends_at <= starts_at"
        except ValidationError:
            if end > start:
                pytest.fail(f"Rejected valid range: {start} - {end}")
        except Exception as e:
            pytest.fail(f"Crash on dates: {type(e).__name__}: {e}")

    @pytest.mark.parametrize("price", [-1, 0, 100, PG_INT4_MAX, PG_INT4_MAX + 1])
    def test_psychologist_price(self, price):
        """Фаззинг цены."""
        candidates = mutate_int(price, 5)

        for p in candidates:
            try:
                prof = PsychologistProfileUpdate(price_per_hour=p)
                if prof.price_per_hour is not None:
                    assert prof.price_per_hour >= 0, f"Negative price accepted: {p}"
            except ValidationError:
                if p >= 0:
                    pytest.fail(f"Rejected valid price: {p}")
            except Exception as e:
                pytest.fail(f"Crash on price {p}: {type(e).__name__}: {e}")

    @pytest.mark.parametrize("slot_id", [-1, 0, 1, PG_INT4_MAX, PG_INT4_MAX + 1])
    def test_appointment_slot_id(self, slot_id):
        """Фаззинг ID слота."""
        candidates = mutate_int(slot_id, 5)

        for sid in candidates:
            try:
                appt = AppointmentCreate(slot_id=sid, notes="test")
                assert 0 < appt.slot_id <= PG_INT4_MAX
            except ValidationError:
                if 0 < sid <= PG_INT4_MAX:
                    pytest.fail(f"Rejected valid slot_id: {sid}")
            except Exception as e:
                pytest.fail(f"Crash on slot_id {sid}: {type(e).__name__}: {e}")

    @pytest.mark.parametrize("notes", [None, "", "A" * 1000, "A" * 1001])
    def test_appointment_notes(self, notes):
        """Фаззинг заметок."""
        candidates = mutate_string(notes or "", 3, max_len=1000)

        for note in candidates:
            try:
                appt = AppointmentCreate(slot_id=1, notes=note if note else None)

                if appt.notes is not None:
                    assert len(appt.notes) <= 1000, f"Notes too long: {len(appt.notes)}"

            except ValidationError:
                if note and len(note) > 1000:
                    pass
                elif note is None or len(note) <= 1000:
                    if not any(c in note for c in ['\x00', '\n']):
                         pytest.fail(f"Rejected valid/short notes (len={len(note) if note else 0}): {repr(note[:50])}")
            except Exception as e:
                pytest.fail(f"Crash on notes: {type(e).__name__}: {e}")