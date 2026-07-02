from app.api.v1.router import api_router
from app.core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if not settings.allowed_origins_list:
    raise ValueError(
        "ALLOWED_ORIGINS environment variable must be set. "
        "Example: ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com"
    )

app = FastAPI(
    title="Сервис онлайн-консультаций с психологом",
    description="REST API для записи к психологам и проведения видеосессий",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(api_router)


@app.get("/", tags=["health"])
def healthcheck():
    return {"status": "ok", "service": "psych-api"}