from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://psych:psych_secret@db:5432/psych_db"

    SECRET_KEY: str = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
