from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.security import hash_password
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Получить профиль текущего пользователя."""
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить имя или пароль текущего пользователя."""
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.password is not None:
        current_user.hashed_password = hash_password(data.password)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Деактивировать собственный аккаунт."""
    current_user.is_active = False
    db.commit()
