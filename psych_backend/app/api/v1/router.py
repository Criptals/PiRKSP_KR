from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, psychologists, schedule, appointments, sessions

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(psychologists.router)
api_router.include_router(schedule.router)
api_router.include_router(appointments.router)
api_router.include_router(sessions.router)
