from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import require_psychologist
from app.db.session import get_db
from app.models.models import Psychologist, ScheduleSlot, User
from app.schemas.schemas import SlotCreate, SlotOut

router = APIRouter(prefix="/schedule", tags=["schedule"])


def _get_my_profile(current_user: User, db: Session) -> Psychologist:
    profile = current_user.psychologist_profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль психолога не найден")
    return profile


@router.get("/", response_model=list[SlotOut])
def get_my_slots(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_psychologist),
):
    """Психолог видит все свои слоты."""
    profile = _get_my_profile(current_user, db)
    return profile.schedule_slots


@router.get("/{psychologist_id}", response_model=list[SlotOut])
def get_slots_by_psychologist(psychologist_id: int, db: Session = Depends(get_db)):
    """Свободные слоты конкретного психолога — для пользователей при записи."""
    profile = db.get(Psychologist, psychologist_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Психолог не найден")
    return [s for s in profile.schedule_slots if s.is_available]


@router.post("/", response_model=SlotOut, status_code=status.HTTP_201_CREATED)
def create_slot(
    data: SlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_psychologist),
):
    """Психолог добавляет новый слот в своё расписание."""
    profile = _get_my_profile(current_user, db)
    overlap = (
        db.query(ScheduleSlot)
        .filter(
            ScheduleSlot.psychologist_id == profile.id,
            ScheduleSlot.starts_at < data.ends_at,
            ScheduleSlot.ends_at > data.starts_at,
        )
        .first()
    )
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Слот пересекается с уже существующим",
        )
    slot = ScheduleSlot(
        psychologist_id=profile.id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_psychologist),
):
    """Психолог удаляет слот из расписания (только если он свободен)."""
    profile = _get_my_profile(current_user, db)
    slot = db.get(ScheduleSlot, slot_id)
    if not slot or slot.psychologist_id != profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Слот не найден")
    if not slot.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить занятый слот — сначала отмените запись",
        )
    db.delete(slot)
    db.commit()
