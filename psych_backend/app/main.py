from app.api.v1.router import api_router
from app.core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Сервис онлайн-консультаций с психологом",
    description="REST API для записи к психологам и проведения видеосессий",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "local" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "local" else None,
)

ALLOWED_ORIGINS = [
]

origins = ALLOWED_ORIGINS if settings.ENVIRONMENT != "local" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/", tags=["health"])
def healthcheck():
    return {"status": "ok", "service": "psych-api"}