import secrets
import uuid
from datetime import datetime, timezone
from aiortc import RTCPeerConnection, RTCSessionDescription
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_psychologist
from app.db.session import get_db, SessionLocal
from app.models.models import Appointment, AppointmentStatus, User, UserRole, VideoSession
from app.schemas.schemas import VideoSessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])
_peer_connections: dict[str, RTCPeerConnection] = {}
_room_clients: dict[str, list[WebSocket]] = {}


def _get_confirmed_appointment(appointment_id: int, db: Session) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    if appointment.status != AppointmentStatus.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сессию можно запустить только для подтверждённой записи",
        )
    return appointment


@router.post("/{appointment_id}/start", response_model=VideoSessionOut)
def start_session(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_psychologist),
):
    """Психолог запускает видеосессию для подтверждённой записи."""
    appointment = _get_confirmed_appointment(appointment_id, db)
    profile = current_user.psychologist_profile
    if appointment.psychologist_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Это не ваша запись")
    if appointment.session and appointment.session.is_active:
        return appointment.session
    if appointment.session:
        session = appointment.session
        session.is_active = True
        session.started_at = datetime.now(timezone.utc)
        session.ended_at = None
    else:
        session = VideoSession(
            appointment_id=appointment.id,
            room_id=secrets.token_urlsafe(16),
            is_active=True,
            started_at=datetime.now(timezone.utc),
        )
        db.add(session)
    appointment.status = AppointmentStatus.completed
    db.commit()
    db.refresh(session)
    return session


@router.post("/{appointment_id}/end", response_model=VideoSessionOut)
def end_session(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_psychologist),
):
    """Психолог завершает видеосессию."""
    appointment = db.get(Appointment, appointment_id)
    if not appointment or not appointment.session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
    profile = current_user.psychologist_profile
    if appointment.psychologist_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Это не ваша сессия")
    session = appointment.session
    session.is_active = False
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{appointment_id}", response_model=VideoSessionOut)
def get_session_info(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о сессии — доступно участникам записи."""
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена")
    is_patient = appointment.patient_id == current_user.id
    is_psychologist = (
        current_user.role == UserRole.psychologist
        and current_user.psychologist_profile
        and appointment.psychologist_id == current_user.psychologist_profile.id
    )
    if not is_patient and not is_psychologist:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой сессии")
    if not appointment.session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия ещё не запущена")
    return appointment.session


@router.websocket("/ws/{room_id}")
async def websocket_signal(websocket: WebSocket, room_id: str):
    """
    Простой сигнальный сервер для WebRTC через WebSocket.

    Клиент подключается к комнате по room_id.
    Все сообщения от одного клиента пересылаются остальным участникам комнаты.
    Формат сообщения — JSON: { "type": "offer"|"answer"|"candidate", ... }
    """
    db = SessionLocal()
    try:
        session_exists = db.query(VideoSession).filter(
            VideoSession.room_id == room_id,
            VideoSession.is_active == True,
        ).first()
        if not session_exists:
            await websocket.close(code=4004, reason="Комната не найдена или сессия неактивна")
            return
    finally:
        db.close()
    await websocket.accept()
    if room_id not in _room_clients:
        _room_clients[room_id] = []
    _room_clients[room_id].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            for client in _room_clients.get(room_id, []):
                if client is not websocket:
                    await client.send_text(data)
    except WebSocketDisconnect:
        clients = _room_clients.get(room_id, [])
        if websocket in clients:
            clients.remove(websocket)
        if not clients:
            _room_clients.pop(room_id, None)


@router.post("/offer/{room_id}")
async def handle_offer(room_id: str, offer: dict, db: Session = Depends(get_db)):
    """
    Принимает WebRTC SDP offer, создаёт RTCPeerConnection и возвращает answer.
    Используется как серверный медиа-участник (например, для записи звонка).
    """
    session = db.query(VideoSession).filter(
        VideoSession.room_id == room_id, VideoSession.is_active == True
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
    pc_key = f"{room_id}_{uuid.uuid4().hex[:8]}"
    pc = RTCPeerConnection()
    _peer_connections[pc_key] = pc
    @pc.on("connectionstatechange")
    async def on_state_change():
        if pc.connectionState in ("failed", "closed", "disconnected"):
            await pc.close()
            _peer_connections.pop(pc_key, None)
    sdp_offer = RTCSessionDescription(sdp=offer["sdp"], type=offer["type"])
    await pc.setRemoteDescription(sdp_offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }
