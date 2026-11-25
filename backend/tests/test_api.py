import uuid
from datetime import date

from app.core.security import create_access_token
from app.models.client import Client
from app.models.user import User


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    assert res_api.json()["status"] == "healthy"


def test_unauthorized_access(client):
    res = client.get("/api/clients")
    assert res.status_code == 401


def test_trainer_login(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "ChangeMe123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "TRAINER"
    assert data["trainer_id"] is not None


def test_client_login_is_refused(client):
    # Client records are for record keeping only: even a correct client password is refused.
    res = client.post(
        "/api/auth/login",
        json={"email": "rahul@example.com", "password": "Client123!"},
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "Only the trainer account can sign in."
    assert "access_token" not in res.json()

    # A wrong password is still a plain 401
    res = client.post(
        "/api/auth/login",
        json={"email": "rahul@example.com", "password": "WrongPassword!"},
    )
    assert res.status_code == 401


def test_client_role_token_is_rejected(client, db_session):
    rahul = (
        db_session.query(Client)
        .join(User, Client.user_id == User.id)
        .filter(User.email == "rahul@example.com")
        .one()
    )
    token = create_access_token(subject=rahul.user_id, role="CLIENT")
    headers = {"Authorization": f"Bearer {token}"}

    for url in [
        "/api/auth/me",
        f"/api/clients/{rahul.id}",
        "/api/clients",
        "/api/sessions",
        f"/api/notes/client/{rahul.id}",
        f"/api/fees/clients/{rahul.id}",
        "/api/notifications",
    ]:
        res = client.get(url, headers=headers)
        assert res.status_code == 403, f"GET {url} -> {res.status_code}"

    # The ?token= media path goes through the same check
    assert client.get(f"/api/clients/{rahul.id}/photo?token={token}").status_code == 403


def test_login_invalid_password(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "WrongPassword!"},
    )
    assert res.status_code == 401


def test_trainer_endpoints_and_client_management(client):
    # 1. Login as Trainer
    login_res = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "ChangeMe123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. View Dashboard
    dash_res = client.get("/api/dashboard/trainer", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["total_clients"] >= 3
    assert dash_data["active_clients"] >= 3

    # 3. List Clients
    clients_res = client.get("/api/clients", headers=headers)
    assert clients_res.status_code == 200
    clients_list = clients_res.json()
    assert len(clients_list) >= 3

    # 4. Create New Client
    new_client_payload = {
        "name": "Vikram Singh",
        "email": "vikram@example.com",
        "phone": "9998887771",
        "age": 28,
        "gender": "Male",
        "height": 175.0,
        "current_weight": 80.0,
        "fitness_goal": "Strength",
        "status": "Active",
    }
    # Clean up if already exists from previous test
    create_res = client.post("/api/clients", json=new_client_payload, headers=headers)
    if create_res.status_code == 400:
        # Already exists, fetch it
        search_res = client.get("/api/clients?search=Vikram", headers=headers)
        created_client = search_res.json()[0]
    else:
        assert create_res.status_code == 201
        created_client = create_res.json()

    assert created_client["name"] == "Vikram Singh"

    # 5. Prevent Duplicate Email
    dup_res = client.post("/api/clients", json=new_client_payload, headers=headers)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"].lower()


def test_session_recording(client):
    # Trainer logs in
    t_login = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "ChangeMe123!"},
    )
    t_token = t_login.json()["access_token"]
    t_headers = {"Authorization": f"Bearer {t_token}"}

    # Get exercises
    ex_res = client.get("/api/exercises", headers=t_headers)
    assert ex_res.status_code == 200
    exercises = ex_res.json()
    assert len(exercises) >= 20
    bench_press_id = next(e["id"] for e in exercises if e["name"] == "Bench Press")

    # Fetch Rahul
    clients_res = client.get("/api/clients?search=Rahul", headers=t_headers)
    rahul_id = clients_res.json()[0]["id"]

    # Record Daily Workout Session for Rahul
    session_payload = {
        "client_id": rahul_id,
        "date": str(date.today()),
        "workout_name": "Chest Focus Special",
        "duration_minutes": 55,
        "notes": "Excellent endurance on bench sets.",
        "status": "COMPLETED",
        "exercises": [
            {
                "exercise_id": bench_press_id,
                "sets_completed": 4,
                "reps": 10,
                "weight_used": 62.5,
                "notes": "Bar speed was very clean",
            }
        ],
    }
    record_res = client.post("/api/sessions", json=session_payload, headers=t_headers)
    assert record_res.status_code == 201
    sess_data = record_res.json()
    assert sess_data["workout_name"] == "Chest Focus Special"
    assert len(sess_data["exercises"]) == 1
    assert sess_data["exercises"][0]["weight_used"] == 62.5

    # The session shows up in Rahul's exercise log
    history_res = client.get(f"/api/sessions?client_id={rahul_id}", headers=t_headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert any(s["id"] == sess_data["id"] and s["workout_name"] == "Chest Focus Special" for s in history)
    assert all(s["client_id"] == rahul_id for s in history)


def test_round2_exercise_filtering_and_equipment(client):
    trainer_login = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "ChangeMe123!"},
    )
    headers = {"Authorization": f"Bearer {trainer_login.json()['access_token']}"}

    # Query with equipment filter
    res = client.get("/api/exercises?equipment=Barbell", headers=headers)
    assert res.status_code == 200
    exercises = res.json()
    assert len(exercises) > 0
    assert all(e["equipment"] == "Barbell" for e in exercises)

    # Query with difficulty filter
    res = client.get("/api/exercises?difficulty=Beginner", headers=headers)
    assert res.status_code == 200
    exercises = res.json()
    assert len(exercises) > 0
    assert all(e["difficulty"] == "Beginner" for e in exercises)


def test_trainer_change_password(client):
    # Use a dedicated trainer so the shared demo trainer's password is never touched
    email = f"pw_trainer_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/auth/register-trainer",
        json={"name": "Password Trainer", "email": email, "password": "OldPassword123!"},
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Fail with wrong current password
    fail_res = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "WrongPassword!", "new_password": "NewPassword123!"},
    )
    assert fail_res.status_code == 400

    # Success with valid current password
    succ_res = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "OldPassword123!", "new_password": "NewPassword123!"},
    )
    assert succ_res.status_code == 200

    # Old password no longer works, new one does
    assert client.post("/api/auth/login", json={"email": email, "password": "OldPassword123!"}).status_code == 401
    new_login = client.post("/api/auth/login", json={"email": email, "password": "NewPassword123!"})
    assert new_login.status_code == 200
    assert new_login.json()["role"] == "TRAINER"
