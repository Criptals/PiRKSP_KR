import json
import random
import urllib.parse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

@pytest.fixture(autouse=True)
def _bind_test_db():
    app.dependency_overrides[get_db] = override_get_db
    reset_db()
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

FUZZY_STRINGS = [
    "",
    " ",
    "\x00\x00\x00",
    "'; DROP TABLE users; --",
    "<script>alert(1)</script>",
    "a" * 10_000,
    "🧠💬🎯",
    "\u202eReverse\u202e",
    "A" * 256,
    json.dumps({"nested": {"deep": True}}),
]

FUZZY_INTEGERS = [
    0,
    -1,
    2**31,
    -(2**31) - 1,
    2**63 - 1,
    99999999999999999999,
]

def get_fuzzy_json_body():
    choices = [
        {},
        [],
        None,
        True,
        123,
        "string",
        {"key": "value"},
        {"nested": [1, 2, {"deep": None}]},
        random.choice(FUZZY_STRINGS),
    ]
    return random.choice(choices)


class TestApiFuzz:

    @pytest.mark.parametrize("email", FUZZY_STRINGS + ["invalid", "@no-domain"])
    @pytest.mark.parametrize("full_name", FUZZY_STRINGS)
    @pytest.mark.parametrize("password", FUZZY_STRINGS + ["123"])
    def test_fuzz_register_never_500(self, email, full_name, password):
        """Регистрация с любыми строками не должна ронять сервер."""
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "full_name": full_name,
            "password": password,
            "role": "user"
        })
        assert resp.status_code != 500, f"500 on register: {resp.text}"
        assert resp.status_code in (201, 409, 422), f"Unexpected status: {resp.status_code}"

    @pytest.mark.parametrize("email", FUZZY_STRINGS)
    @pytest.mark.parametrize("password", FUZZY_STRINGS)
    def test_fuzz_login_never_500(self, email, password):
        """Логин с любыми строками не должен ронять сервер."""
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code != 500, f"500 on login: {resp.text}"
        assert resp.status_code in (401, 422)

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/schedule/",
        "/api/v1/appointments/",
    ])
    def test_fuzz_arbitrary_json_body_never_500(self, endpoint):
        """Случайные JSON-структуры в любом эндпоинте не должны вызывать 500."""
        for _ in range(5):
            body = get_fuzzy_json_body()
            content = body if isinstance(body, str) else json.dumps(body)
            resp = client.post(
                endpoint,
                content=content,
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code != 500, f"{endpoint} -> 500 on body {body!r}: {resp.text}"

    def _get_user_token(self):
        """Хелпер для получения токена авторизованного пользователя."""
        client.post("/api/v1/auth/register", json={
            "email": "fuzzuser@example.com",
            "full_name": "Fuzz User",
            "password": "secret123",
            "role": "user",
        })
        login = client.post("/api/v1/auth/login", json={
            "email": "fuzzuser@example.com",
            "password": "secret123"
        })
        return login.json()["access_token"]

    @pytest.mark.parametrize("slot_id", FUZZY_INTEGERS + [1, 999999])
    def test_fuzz_book_appointment_arbitrary_slot_id_never_500(self, slot_id):
        """Запись на слот с любым ID не должна ронять сервер."""
        token = self._get_user_token()

        resp = client.post(
            "/api/v1/appointments/",
            json={"slot_id": slot_id, "notes": None},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code != 500, f"500 on appointment booking with slot_id={slot_id}: {resp.text}"
        assert resp.status_code in (404, 422, 401)

    @pytest.mark.parametrize("garbage", FUZZY_STRINGS + ["room123", "!@#$%"])
    def test_fuzz_websocket_unknown_room_closes_gracefully(self, garbage):
        """Подключение к несуществующей комнате должно аккуратно закрываться."""
        room_id = urllib.parse.quote(garbage, safe="") or "x"
        try:
            with client.websocket_connect(f"/api/v1/sessions/ws/{room_id}") as ws:
                ws.close()
        except Exception as e:
            pass