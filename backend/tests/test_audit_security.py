from app.models.client import Client


def test_audit_auth_and_roles(client):
    # 1. Unauthorized request
    res = client.get("/api/dashboard/trainer")
    assert res.status_code == 401

    # 2. Invalid trainer credentials
    res = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "BadPassword123!"},
    )
    assert res.status_code == 401

    # 3. Valid trainer login
    res = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "ChangeMe123!"},
    )
    assert res.status_code == 200
    t_data = res.json()
    assert t_data["role"] == "TRAINER"


def test_audit_client_management_crud(client):
    trainer_login = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "ChangeMe123!"},
    )
    t_headers = {"Authorization": f"Bearer {trainer_login.json()['access_token']}"}

    # Create new client
    new_email = "audit_user_1@example.com"
    payload = {
        "name": "Audit Athlete",
        "email": new_email,
        "phone": "9876543210",
        "age": 25,
        "gender": "Female",
        "height": 168.0,
        "current_weight": 62.0,
        "fitness_goal": "Fat Loss",
        "status": "Active",
    }
    create_res = client.post("/api/clients", json=payload, headers=t_headers)
    assert create_res.status_code in [201, 400]
    if create_res.status_code == 201:
        created = create_res.json()
        client_id = created["id"]
    else:
        # Fetch existing by specific email
        search_res = client.get(f"/api/clients?search={new_email}", headers=t_headers)
        client_id = search_res.json()[0]["id"]

    # Prevent duplicate email
    dup_res = client.post("/api/clients", json=payload, headers=t_headers)
    assert dup_res.status_code == 400

    # Read client details
    get_res = client.get(f"/api/clients/{client_id}", headers=t_headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Audit Athlete"

    # Update client details
    update_res = client.put(
        f"/api/clients/{client_id}",
        json={"current_weight": 61.5, "fitness_goal": "Endurance"},
        headers=t_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["current_weight"] == 61.5
    assert update_res.json()["fitness_goal"] == "Endurance"

    # Typed update body: invalid values are rejected
    bad_res = client.put(
        f"/api/clients/{client_id}",
        json={"current_weight": -5},
        headers=t_headers,
    )
    assert bad_res.status_code == 422


def test_audit_exercise_management_and_filters(client):
    trainer_login = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "ChangeMe123!"},
    )
    t_headers = {"Authorization": f"Bearer {trainer_login.json()['access_token']}"}

    ex_name = "Audit Bulgarian Split Squat"
    payload = {
        "name": ex_name,
        "muscle_group": "Legs",
        "equipment": "Dumbbell",
        "difficulty": "Intermediate",
        "description": "Rear foot elevated single-leg squat",
    }
    create_res = client.post("/api/exercises", json=payload, headers=t_headers)
    assert create_res.status_code in [201, 400]
    if create_res.status_code == 201:
        ex_id = create_res.json()["id"]
    else:
        search_res = client.get(f"/api/exercises?search={ex_name}", headers=t_headers)
        ex_id = search_res.json()[0]["id"]

    # Filter with equipment and difficulty
    filter_res = client.get(
        "/api/exercises?equipment=Dumbbell&difficulty=Intermediate", headers=t_headers
    )
    assert filter_res.status_code == 200
    items = filter_res.json()
    assert any(e["id"] == ex_id for e in items)

    # Update exercise
    update_res = client.put(
        f"/api/exercises/{ex_id}",
        json={"description": "Updated form cue: keep chest tall"},
        headers=t_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated form cue: keep chest tall"


def test_audit_trainer_dashboard_metrics(client, db_session):
    trainer_login = client.post(
        "/api/auth/login",
        json={"email": "trainer@example.com", "password": "ChangeMe123!"},
    )
    trainer_id = trainer_login.json()["trainer_id"]
    t_headers = {"Authorization": f"Bearer {trainer_login.json()['access_token']}"}

    dash_res = client.get("/api/dashboard/trainer", headers=t_headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()

    # Exact response shape: no extra fields beyond what the dashboard renders
    assert set(dash) == {
        "total_clients", "active_clients", "today_attendance", "billing", "upcoming_dues", "recent_clients",
        "attendance_trend", "recent_activity",
    }
    assert set(dash["today_attendance"]) == {"present", "absent", "late", "unmarked"}
    assert set(dash["billing"]) == {
        "currency", "outstanding_total", "overdue_total", "overdue_count", "collected_this_month", "unread_alerts",
    }
    assert isinstance(dash["upcoming_dues"], list)
    for due in dash["upcoming_dues"]:
        assert set(due) == {"fee_id", "client_id", "client_name", "due_date", "balance", "status"}
    assert isinstance(dash["recent_clients"], list) and len(dash["recent_clients"]) <= 5

    # Counts match the trainer's roster
    db_session.expire_all()
    roster = db_session.query(Client).filter(Client.trainer_id == trainer_id)
    assert dash["total_clients"] == roster.count() >= 3
    assert dash["active_clients"] == roster.filter(Client.status == "Active").count()
