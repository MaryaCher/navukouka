import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

# Добавляем корень проекта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.db.database import Base, get_db
from app.db.models import User, Role, ModelVersion
from app.core.security import hash_password

# Используем SQLite в памяти для тестов, чтобы не трогать реальную MySQL
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # --- ДОБАВЛЯЕМ СОЗДАНИЕ БАЗОВЫХ РОЛЕЙ ---
    from app.db.models import Role
    user_role = Role(name="user", description="Обычный пользователь")
    admin_role = Role(name="admin", description="Администратор")
    session.add(user_role)
    session.add(admin_role)
    session.commit()
    # ----------------------------------------

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()



@pytest.fixture
def test_user(db_session):
    """Создает тестового пользователя в БД"""
    # Роль user уже создана в db_session
    role = db_session.query(Role).filter_by(name="user").first()

    user = User(
        username="testuser",
        password_hash=hash_password("testpassword"),
        role_id=role.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def auth_headers(client, test_user):
    """Возвращает заголовки с JWT токеном"""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpassword"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}