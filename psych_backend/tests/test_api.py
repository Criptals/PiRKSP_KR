import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.main import app


SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def register(email="user@test.com", password="pass123", role="user", name="Тест Тестов"):
    return client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "role": role, "full_name": name
    })


def login(email="user@test.com", password="pass123"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json().get("access_token")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_healthcheck():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_user():
    r = register()
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "user@test.com"
    assert data["role"] == "user"


def test_register_duplicate_email():
    register()
    r = register()
    assert r.status_code == 409


def test_register_psychologist():
    r = register(email="psych@test.com", role="psychologist", name="Иван Иванов")
    assert r.status_code == 201
    assert r.json()["role"] == "psychologist"


def test_login_success():
    register()
    token = login()
    assert token is not None


def test_login_wrong_password():
    register()
    r = client.post("/api/v1/auth/login", json={"email": "user@test.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_get_me():
    register()
    token = login()
    r = client.get("/api/v1/users/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["email"] == "user@test.com"


def test_update_me():
    register()
    token = login()
    r = client.patch("/api/v1/users/me", json={"full_name": "Новое Имя"}, headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["full_name"] == "Новое Имя"


def test_list_psychologists():
    register(email="psych@test.com", role="psychologist", name="Психолог Петров")
    r = client.get("/api/v1/psychologists/")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_create_schedule_slot():
    register(email="psych@test.com", role="psychologist", name="Психолог")
    token = login(email="psych@test.com")
    r = client.post(
        "/api/v1/schedule/",
        json={"starts_at": "2025-06-01T10:00:00", "ends_at": "2025-06-01T11:00:00"},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    assert r.json()["is_available"] is True


def test_book_appointment():
    register(email="psych@test.com", role="psychologist", name="Психолог")
    psych_token = login(email="psych@test.com")

    slot_r = client.post(
        "/api/v1/schedule/",
        json={"starts_at": "2025-06-01T10:00:00", "ends_at": "2025-06-01T11:00:00"},
        headers=auth_headers(psych_token),
    )
    slot_id = slot_r.json()["id"]

    register()
    user_token = login()
    r = client.post(
        "/api/v1/appointments/",
        json={"slot_id": slot_id, "notes": "Хочу записаться"},
        headers=auth_headers(user_token),
    )
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
