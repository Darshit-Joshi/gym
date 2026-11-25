import pytest
import concurrent.futures
from app.models.user import User
from app.models.trainer import Trainer
from app.models.client import Client
from app.core.security import verify_password, get_password_hash


@pytest.fixture(scope="module", autouse=True)
def module_trainer_lifecycle(db_session):
    # Before tests in this module: ensure demo trainer state is active
    trainer = db_session.query(Trainer).first()
    if trainer:
        user = trainer.user
        if user:
            user.email = "trainer@example.com"
            user.password_hash = get_password_hash("ChangeMe123!")
        trainer.name = "Demo Trainer"
        trainer.is_demo = True
        db_session.commit()
    yield
    # After module tests: restore demo trainer state so facility remains ready for user
    db_session.expire_all()
    trainer = db_session.query(Trainer).first()
    if trainer:
        user = trainer.user
        if user:
            user.email = "trainer@example.com"
            user.password_hash = get_password_hash("ChangeMe123!")
        trainer.name = "Demo Trainer"
        trainer.is_demo = True
        db_session.commit()


def test_setup_status_does_not_expose_private_info(client):
    res = client.get("/api/auth/setup-status")
    assert res.status_code == 200
    data = res.json()
    assert "is_setup_completed" in data
    assert "has_trainer" in data
    assert "can_register_trainer" in data
    # Ensure no private data is exposed
    assert "trainer_name" not in data
    assert "email" not in data
    assert "password" not in data


def test_registration_validation_rules(client):
    # Name too short
    res = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "A",
            "email": "valid.email@example.com",
            "password": "ValidPassword123!",
        },
    )
    assert res.status_code == 422

    # Invalid email
    res = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Marcus Vance",
            "email": "not-an-email",
            "password": "ValidPassword123!",
        },
    )
    assert res.status_code == 422

    # Password too short (< 8 chars)
    res = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Marcus Vance",
            "email": "valid.email@example.com",
            "password": "short",
        },
    )
    assert res.status_code == 422


def test_registration_rejects_duplicate_email_of_client(client):
    # rahul@example.com already exists as an athlete
    res = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Marcus Vance",
            "email": "rahul@example.com",
            "password": "ValidPassword123!",
        },
    )
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()


def test_genuine_trainer_registration_success(client, db_session):
    # Count existing clients before registration
    initial_client_count = db_session.query(Client).count()

    real_trainer_payload = {
        "name": "Marcus Vance",
        "email": "marcus.vance@onecountry.com",
        "password": "RealTrainerPass2026!",
        "phone": "+1-555-8888",
    }

    res = client.post("/api/auth/register-trainer", json=real_trainer_payload)
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "TRAINER"
    assert data["name"] == "Marcus Vance"
    assert data["trainer_id"] is not None

    # Verify directly in database
    db_session.expire_all()
    user = db_session.query(User).filter(User.email == "marcus.vance@onecountry.com").first()
    assert user is not None
    assert user.role == "TRAINER"
    assert user.is_active is True
    # Password must be securely hashed, never plaintext
    assert user.password_hash != "RealTrainerPass2026!"
    assert verify_password("RealTrainerPass2026!", user.password_hash) is True

    # Verify trainer record
    trainer = db_session.query(Trainer).filter(Trainer.user_id == user.id).first()
    assert trainer is not None
    assert trainer.name == "Marcus Vance"
    assert trainer.phone == "+1-555-8888"
    assert trainer.is_demo is False

    # Verify all existing client records remain intact
    current_client_count = db_session.query(Client).count()
    assert current_client_count == initial_client_count


def test_registered_trainer_login_workflow(client):
    # 1. Login with correct credentials
    login_res = client.post(
        "/api/auth/login",
        json={
            "email": "marcus.vance@onecountry.com",
            "password": "RealTrainerPass2026!",
        },
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["role"] == "TRAINER"
    assert login_data["name"] == "Marcus Vance"

    # 2. Login with incorrect password rejected
    bad_pwd_res = client.post(
        "/api/auth/login",
        json={
            "email": "marcus.vance@onecountry.com",
            "password": "IncorrectPassword!",
        },
    )
    assert bad_pwd_res.status_code == 401
    assert "invalid email or password" in bad_pwd_res.json()["detail"].lower()


def test_second_trainer_registration_allowed(client):
    # Registering another independent trainer must succeed
    res = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Second Trainer",
            "email": "second.trainer@onecountry.com",
            "password": "SecondPassword123!",
        },
    )
    assert res.status_code == 201
    assert res.json()["role"] == "TRAINER"
    assert res.json()["name"] == "Second Trainer"

    # Also check /setup-trainer alias
    alias_res = client.post(
        "/api/auth/setup-trainer",
        json={
            "name": "Third Trainer Attempt",
            "email": "third.trainer@onecountry.com",
            "password": "ThirdPassword123!",
        },
    )
    assert alias_res.status_code == 201
    assert alias_res.json()["role"] == "TRAINER"


def test_setup_status_closed_after_registration(client):
    res = client.get("/api/auth/setup-status")
    assert res.status_code == 200
    data = res.json()
    assert data["has_trainer"] is True
    assert data["can_register_trainer"] is True
    assert data["is_setup_completed"] is True


def test_multiple_trainer_registrations_succeed(client):
    # Multiple trainer registrations with distinct emails must all succeed
    for i in range(3):
        res = client.post(
            "/api/auth/register-trainer",
            json={
                "name": f"Trainer Multi {i}",
                "email": f"trainer_multi_{i}@test.com",
                "password": "ConcurrentPass123!",
            },
        )
        assert res.status_code == 201
