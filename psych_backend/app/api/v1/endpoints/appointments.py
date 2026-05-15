from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_psychologist, require_user
from app.db.session import get_db
from app.models.models import Appointment, AppointmentStatus, Psychologist, ScheduleSlot, User, UserRole
from app.schemas.schemas import AppointmentCreate, AppointmentOut, AppointmentStatusUpdate

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("/", response_model=list[AppointmentOut])
def list_my_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Пользователь видит свои записи.
    Психолог видит все записи к себе.
    """
    if current_user.role == UserRole.user:
        return (
            db.query(Appointment)
            .filter(Appointment.patient_id == current_user.id)
            .all()
        )
    else:
        profile = current_user.psychologist_profile
        if not profile:
            return []
        return db.query(Appointment).filter(Appointment.psychologist_id == profile.id).all()


@router.post("/", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Пользователь записывается к психологу на свободный слот."""
    slot = db.get(ScheduleSlot, data.slot_id)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Слот не найден")
    if not slot.is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Этот слот уже занят",
        )
    appointment = Appointment(
        patient_id=current_user.id,
        psychologist_id=slot.psychologist_id,
        slot_id=slot.id,
        notes=data.notes,
    )
    slot.is_available = False
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.patch("/{appointment_id}/status", response_model=AppointmentOut)
def update_appointment_status(
    appointment_id: int,
    data: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_psychologist),
):
    """Психолог подтверждает или отменяет запись."""
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    profile = current_user.psychologist_profile
    if appointment.psychologist_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Это не ваша запись")
    if data.status == AppointmentStatus.cancelled:
        appointment.slot.is_available = True
    appointment.status = data.status
    db.commit()
    db.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_my_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Пользователь отменяет свою запись."""
    appointment = db.get(Appointment, appointment_id)
    if not appointment or appointment.patient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    if appointment.status == AppointmentStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отменить завершённую сессию",
        )
    appointment.slot.is_available = True
    appointment.status = AppointmentStatus.cancelled
    db.commit()
