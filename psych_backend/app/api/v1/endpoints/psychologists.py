from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_psychologist
from app.db.session import get_db
from app.models.models import Psychologist, User
from app.schemas.schemas import PsychologistOut, PsychologistProfileUpdate

router = APIRouter(prefix="/psychologists", tags=["psychologists"])


@router.get("/", response_model=list[PsychologistOut])
def list_psychologists(db: Session = Depends(get_db)):
    """Список всех психологов — доступен всем."""
    return db.query(Psychologist).join(Psychologist.user).filter(User.is_active == True).all()


@router.get("/{psychologist_id}", response_model=PsychologistOut)
def get_psychologist(psychologist_id: int, db: Session = Depends(get_db)):
    """Профиль конкретного психолога."""
    profile = db.get(Psychologist, psychologist_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Психолог не найден")
    return profile


@router.patch("/me", response_model=PsychologistOut)
def update_my_profile(
    data: PsychologistProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_psychologist),
):
    """Психолог обновляет собственный профиль."""
    profile = current_user.psychologist_profile
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
