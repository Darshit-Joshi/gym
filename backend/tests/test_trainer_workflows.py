"""Daily trainer workflows: roster rules, duplicate-safe attendance, client edits and
removal, workout logging with sets/reps, and the dashboard activity feed."""
import uuid
from datetime import timedelta

from app.core.timezone import today_gym


def _register_trainer(client):
    res = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Workflow Trainer",
            "email": f"wf_{uuid.uuid4().hex[:10]}@example.com",
            "password": "TrainerPass123!",
        },
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _create_client(client, headers, **extra):
    body = {"name": extra.pop("name", f"Client {uuid.uuid4().hex[:4]}"), **extra}
    res = client.post("/api/clients", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _mark(client, headers, client_id, d, st="PRESENT"):
    return client.post(
        "/api/attendance",
        json={"client_id": client_id, "date": d.isoformat(), "status": st},
        headers=headers,
    )


def _exercise_ids(client, headers, n):
    res = client.get("/api/exercises", headers=headers)
    assert res.status_code == 200
    return [e["id"] for e in res.json()[:n]]


# ------------------------------------------------------------------ attendance

def test_marking_twice_keeps_one_record_per_day(client):
    headers = _register_trainer(client)
    c = _create_client(client, headers)
    today = today_gym()

    first = _mark(client, headers, c["id"], today, "PRESENT")
    second = _mark(client, headers, c["id"], today, "LATE")
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    history = client.get(f"/api/attendance/client/{c['id']}", headers=headers).json()
    assert history["total_recorded"] == 1
    assert history["records"][0]["status"] == "LATE"


def test_attendance_cannot_be_marked_in_the_future(client):
    headers = _register_trainer(client)
    c = _create_client(client, headers)
    res = _mark(client, headers, c["id"], today_gym() + timedelta(days=1))
    assert res.status_code == 400
    assert "future" in res.json()["detail"]


def test_daily_sheet_lists_only_clients_currently_training(client):
    headers = _register_trainer(client)
    today = today_gym()
    active = _create_client(client, headers, name="Sheet Active")
    inactive = _create_client(client, headers, name="Sheet Inactive", status="Inactive")
    archived = _create_client(client, headers, name="Sheet Archived")
    assert client.post(f"/api/clients/{archived['id']}/archive", headers=headers).status_code == 200

    sheet = client.get("/api/attendance", headers=headers).json()
    assert [c["client_name"] for c in sheet["clients"]] == ["Sheet Active"]
    assert sheet["unmarked_count"] == 1

    # A client who already has a record that day stays visible after being deactivated
    yesterday = today - timedelta(days=1)
    assert _mark(client, headers, inactive["id"], yesterday).status_code == 200
    past = client.get("/api/attendance", params={"attendance_date": yesterday.isoformat()}, headers=headers).json()
    assert {c["client_name"] for c in past["clients"]} == {"Sheet Active", "Sheet Inactive"}
    assert active["id"] in {c["client_id"] for c in past["clients"]}


# ------------------------------------------------------------------ clients

def test_current_filter_hides_archived_clients(client):
    headers = _register_trainer(client)
    keep = _create_client(client, headers, name="Current Keep")
    gone = _create_client(client, headers, name="Current Gone")
    client.post(f"/api/clients/{gone['id']}/archive", headers=headers)

    res = client.get("/api/clients", params={"status": "current", "page": 1, "page_size": 50}, headers=headers)
    names = {c["name"] for c in res.json()["items"]}
    assert keep["name"] in names and gone["name"] not in names


def test_edit_client_email_status_and_age(client):
    headers = _register_trainer(client)
    c = _create_client(client, headers, name="Edit Me")
    other = _create_client(client, headers, email=f"taken_{uuid.uuid4().hex[:6]}@example.com")

    res = client.put(f"/api/clients/{c['id']}", json={"email": "edited@example.com", "date_of_birth": "2000-01-01"}, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["email"] == "edited@example.com"
    assert body["age"] is not None and body["age"] >= 25

    dup = client.put(f"/api/clients/{c['id']}", json={"email": other["email"]}, headers=headers)
    assert dup.status_code == 400

    cleared = client.put(f"/api/clients/{c['id']}", json={"email": ""}, headers=headers)
    assert cleared.status_code == 200 and cleared.json()["email"] is None

    assert client.put(f"/api/clients/{c['id']}", json={"name": None}, headers=headers).status_code == 400
    assert client.put(f"/api/clients/{c['id']}", json={"status": "Banana"}, headers=headers).status_code == 400


def test_permanent_delete_requires_archive_first(client):
    headers = _register_trainer(client)
    c = _create_client(client, headers, name="Delete Me")
    assert _mark(client, headers, c["id"], today_gym()).status_code == 200

    early = client.delete(f"/api/clients/{c['id']}/permanent", headers=headers)
    assert early.status_code == 409

    client.post(f"/api/clients/{c['id']}/archive", headers=headers)
    res = client.delete(f"/api/clients/{c['id']}/permanent", headers=headers)
    assert res.status_code == 200, res.text
    assert client.get(f"/api/clients/{c['id']}", headers=headers).status_code == 404


def test_permanent_delete_is_scoped_to_own_clients(client):
    owner = _register_trainer(client)
    intruder = _register_trainer(client)
    c = _create_client(client, owner)
    client.post(f"/api/clients/{c['id']}/archive", headers=owner)
    assert client.delete(f"/api/clients/{c['id']}/permanent", headers=intruder).status_code == 404


# ------------------------------------------------------------------ workouts

def test_day_log_stores_sets_reps_and_weight(client):
    headers = _register_trainer(client)
    c = _create_client(client, headers)
    ex1, ex2 = _exercise_ids(client, headers, 2)
    today = today_gym().isoformat()

    res = client.put(
        "/api/sessions/day",
        json={
            "client_id": c["id"],
            "date": today,
            "exercise_ids": [ex1, ex2],
            "details": [{"exercise_id": ex1, "sets_completed": 4, "reps": 10, "weight_used": 60}],
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    by_id = {e["exercise_id"]: e for e in res.json()["exercises"]}
    assert (by_id[ex1]["sets_completed"], by_id[ex1]["reps"], by_id[ex1]["weight_used"]) == (4, 10, 60)
    assert by_id[ex2]["sets_completed"] is None

    # Saving again without details keeps what was stored; still one record for the day
    again = client.put(
        "/api/sessions/day",
        json={"client_id": c["id"], "date": today, "exercise_ids": [ex1, ex2]},
        headers=headers,
    )
    assert {e["exercise_id"]: e["reps"] for e in again.json()["exercises"]}[ex1] == 10
    days = client.get("/api/sessions", params={"client_id": c["id"]}, headers=headers).json()
    assert len(days) == 1


def test_day_log_rejects_future_dates_and_limit_works(client):
    headers = _register_trainer(client)
    c = _create_client(client, headers)
    (ex,) = _exercise_ids(client, headers, 1)
    future = (today_gym() + timedelta(days=2)).isoformat()
    res = client.put("/api/sessions/day", json={"client_id": c["id"], "date": future, "exercise_ids": [ex]}, headers=headers)
    assert res.status_code == 400

    for back in range(3):
        d = (today_gym() - timedelta(days=back)).isoformat()
        assert client.put("/api/sessions/day", json={"client_id": c["id"], "date": d, "exercise_ids": [ex]}, headers=headers).status_code == 200
    latest = client.get("/api/sessions", params={"client_id": c["id"], "limit": 2}, headers=headers).json()
    assert [s["date"] for s in latest] == [today_gym().isoformat(), (today_gym() - timedelta(days=1)).isoformat()]


# ------------------------------------------------------------------ dashboard

def test_dashboard_trend_and_recent_activity(client):
    headers = _register_trainer(client)
    c = _create_client(client, headers, name="Feed Client")
    today = today_gym()
    _mark(client, headers, c["id"], today, "PRESENT")
    _mark(client, headers, c["id"], today - timedelta(days=1), "ABSENT")
    (ex,) = _exercise_ids(client, headers, 1)
    client.put("/api/sessions/day", json={"client_id": c["id"], "date": today.isoformat(), "exercise_ids": [ex]}, headers=headers)

    dash = client.get("/api/dashboard/trainer", headers=headers).json()
    trend = dash["attendance_trend"]
    assert len(trend) == 7 and trend[-1]["date"] == today.isoformat()
    assert trend[-1]["checked_in"] == 1 and trend[-2]["absent"] == 1

    kinds = {a["kind"] for a in dash["recent_activity"]}
    assert {"ATTENDANCE", "WORKOUT", "CLIENT_ADDED"} <= kinds
    assert all(a["client_name"] == "Feed Client" for a in dash["recent_activity"])


def test_client_list_carries_payment_status(client):
    headers = _register_trainer(client)
    today = today_gym()
    no_plan = _create_client(client, headers, name="Pay NoPlan")
    late = _create_client(client, headers, name="Pay Late")
    plan = client.post("/api/fees/plans", json={"name": "Monthly", "price": "1000", "duration_months": 1}, headers=headers).json()
    start = (today - timedelta(days=40)).isoformat()
    assert client.put(f"/api/fees/clients/{late['id']}/membership", json={"plan_id": plan["id"], "billing_start_date": start}, headers=headers).status_code == 200

    res = client.get("/api/clients", params={"page": 1, "page_size": 50}, headers=headers).json()
    by_name = {c["name"]: c for c in res["items"]}
    assert by_name["Pay NoPlan"]["payment_status"] == "NO_PLAN"
    assert by_name["Pay Late"]["payment_status"] == "OVERDUE"
    assert by_name["Pay Late"]["outstanding_amount"] >= 1000


def test_trainer_registration_can_be_closed(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ALLOW_TRAINER_REGISTRATION", False)
    res = client.post(
        "/api/auth/register-trainer",
        json={"name": "Late Comer", "email": f"late_{uuid.uuid4().hex[:8]}@example.com", "password": "TrainerPass123!"},
    )
    assert res.status_code == 403
    assert client.get("/api/auth/setup-status").json()["can_register_trainer"] is False
