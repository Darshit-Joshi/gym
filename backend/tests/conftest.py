import os
import sys
from pathlib import Path

# The background scheduler talks to the real DATABASE_URL; never run it under tests.
os.environ["SCHEDULER_ENABLED"] = "false"
# Keep test photos out of backend/uploads, and never use a real bucket from .env.
import tempfile
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="gym-test-uploads-")
os.environ["STORAGE_BACKEND"] = "local"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.core.database import Base
from app.api.deps import get_db
from app.models.trainer import Trainer
from app.core.security import get_password_hash
from app.seed import seed_database

# ISOLATED IN-MEMORY SQLITE DATABASE FOR AUTOMATED TESTING
# Ensures tests NEVER insert, update, or pollute the production/live PostgreSQL database!
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override FastAPI get_db dependency to point to isolated in-memory SQLite
app.dependency_overrides[get_db] = override_get_db



@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Create all tables in SQLite
    Base.metadata.create_all(bind=test_engine)

    # Seed the isolated test database
    db = TestingSessionLocal()
    try:
        seed_database(force=True, db=db)
    finally:
        db.close()

    yield

    # Drop all tables after test session
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def init_test_session_trainer(db_session, setup_test_database):
    trainer = db_session.query(Trainer).first()
    if trainer and trainer.user:
        trainer.user.email = "trainer@example.com"
        trainer.user.password_hash = get_password_hash("ChangeMe123!")
        trainer.name = "Demo Trainer"
        trainer.is_demo = False
        db_session.commit()
    yield
    db_session.expire_all()
    trainer = db_session.query(Trainer).first()
    if trainer and trainer.user:
        trainer.user.email = "trainer@example.com"
        trainer.user.password_hash = get_password_hash("ChangeMe123!")
        trainer.name = "Demo Trainer"
        trainer.is_demo = True
        db_session.commit()


@pytest.fixture
def active_trainer_credentials(db_session):
    trainer = db_session.query(Trainer).first()
    if trainer and trainer.user:
        email = trainer.user.email
        pwd = "RealTrainerPass2026!" if "marcus" in email else "ChangeMe123!"
        return email, pwd
    return "trainer@example.com", "ChangeMe123!"


@pytest.fixture
def trainer_auth_headers(client, active_trainer_credentials):
    email, pwd = active_trainer_credentials
    res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    token = res.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}
