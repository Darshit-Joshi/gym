import pytest
from datetime import date, timedelta


def _get_auth_header(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_multi_trainer_registration_and_authentication(client):
    # 1. Trainer A registers
    res_a = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Trainer Alice",
            "email": "alice.trainer@testgym.com",
            "password": "Password123!",
            "phone": "+1-555-1111",
        },
    )
    assert res_a.status_code == 201
    data_a = res_a.json()
    assert data_a["role"] == "TRAINER"
    assert data_a["name"] == "Trainer Alice"

    # 2. Trainer B registers independently
    res_b = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Trainer Bob",
            "email": "bob.trainer@testgym.com",
            "password": "Password123!",
            "phone": "+1-555-2222",
        },
    )
    assert res_b.status_code == 201
    data_b = res_b.json()
    assert data_b["role"] == "TRAINER"
    assert data_b["name"] == "Trainer Bob"
    assert data_b["trainer_id"] != data_a["trainer_id"]

    # 3. Trainer C registers independently
    res_c = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Trainer Charlie",
            "email": "charlie.trainer@testgym.com",
            "password": "Password123!",
            "phone": "+1-555-3333",
        },
    )
    assert res_c.status_code == 201
    data_c = res_c.json()
    assert data_c["role"] == "TRAINER"
    assert data_c["trainer_id"] not in (data_a["trainer_id"], data_b["trainer_id"])

    # 4. Duplicate email rejected across trainers
    res_dup = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Duplicate Alice",
            "email": "alice.trainer@testgym.com",
            "password": "Password123!",
        },
    )
    assert res_dup.status_code == 400


def test_client_roster_isolation_between_trainers(client):
    headers_a = _get_auth_header(client, "alice.trainer@testgym.com", "Password123!")
    headers_b = _get_auth_header(client, "bob.trainer@testgym.com", "Password123!")

    # Trainer A creates Client A1
    res_ca = client.post(
        "/api/clients",
        json={
            "name": "Alice Athlete One",
            "email": "alice.athlete1@client.com",
            "phone": "555-0101",
            "fitness_goal": "Strength",
            "gender": "Female",
            "age": 28,
        },
        headers=headers_a,
    )
    assert res_ca.status_code == 201
    client_a1_id = res_ca.json()["id"]

    # Trainer B creates Client B1
    res_cb = client.post(
        "/api/clients",
        json={
            "name": "Bob Athlete One",
            "email": "bob.athlete1@client.com",
            "phone": "555-0202",
            "fitness_goal": "Hypertrophy",
            "gender": "Male",
            "age": 32,
        },
        headers=headers_b,
    )
    assert res_cb.status_code == 201
    client_b1_id = res_cb.json()["id"]

    # Trainer A lists clients: must see Client A1 and NEVER Client B1
    list_a = client.get("/api/clients", headers=headers_a).json()
    client_ids_a = [c["id"] for c in list_a]
    assert client_a1_id in client_ids_a
    assert client_b1_id not in client_ids_a

    # Trainer B lists clients: must see Client B1 and NEVER Client A1
    list_b = client.get("/api/clients", headers=headers_b).json()
    client_ids_b = [c["id"] for c in list_b]
    assert client_b1_id in client_ids_b
    assert client_a1_id not in client_ids_b

    # Trainer A attempts cross-trainer access to Client B1
    # GET
    res_cross_get = client.get(f"/api/clients/{client_b1_id}", headers=headers_a)
    assert res_cross_get.status_code == 403

    # PUT
    res_cross_put = client.put(f"/api/clients/{client_b1_id}", json={"name": "Hacked Name"}, headers=headers_a)
    assert res_cross_put.status_code == 403

    # DELETE
    res_cross_del = client.delete(f"/api/clients/{client_b1_id}", headers=headers_a)
    assert res_cross_del.status_code in (403, 404)

    # ARCHIVE
    res_cross_arch = client.post(f"/api/clients/{client_b1_id}/archive", headers=headers_a)
    assert res_cross_arch.status_code in (403, 404)

    # Client B1 untouched by the attempts above
    b1 = client.get(f"/api/clients/{client_b1_id}", headers=headers_b).json()
    assert b1["name"] == "Bob Athlete One"
    assert b1["status"] == "Active"


def test_session_history_isolation_between_trainers(client):
    headers_a = _get_auth_header(client, "alice.trainer@testgym.com", "Password123!")
    headers_b = _get_auth_header(client, "bob.trainer@testgym.com", "Password123!")

    client_a1 = client.get("/api/clients?search=Alice+Athlete", headers=headers_a).json()[0]
    client_b1 = client.get("/api/clients?search=Bob+Athlete", headers=headers_b).json()[0]

    exercises = client.get("/api/exercises", headers=headers_a).json()
    bench_id = next(e["id"] for e in exercises if "Bench" in e["name"])

    # Trainer A logs session for Client A1
    res_sa = client.post(
        "/api/sessions",
        json={
            "client_id": client_a1["id"],
            "workout_name": "Alice Monday Workout",
            "date": str(date.today()),
            "duration_minutes": 55,
            "notes": "Great intensity",
            "status": "COMPLETED",
            "exercises": [
                {"exercise_id": bench_id, "sets_completed": 4, "reps": 8, "weight_used": 75.0}
            ],
        },
        headers=headers_a,
    )
    assert res_sa.status_code == 201
    session_a_id = res_sa.json()["id"]

    # Trainer B logs session for Client B1
    res_sb = client.post(
        "/api/sessions",
        json={
            "client_id": client_b1["id"],
            "workout_name": "Bob Tuesday Workout",
            "date": str(date.today()),
            "duration_minutes": 45,
            "notes": "Solid volume",
            "status": "COMPLETED",
            "exercises": [
                {"exercise_id": bench_id, "sets_completed": 3, "reps": 12, "weight_used": 60.0}
            ],
        },
        headers=headers_b,
    )
    assert res_sb.status_code == 201
    session_b_id = res_sb.json()["id"]

    # Trainer A lists sessions: sees Session A, never Session B
    sessions_a = client.get("/api/sessions", headers=headers_a).json()
    sess_ids_a = [s["id"] for s in sessions_a]
    assert session_a_id in sess_ids_a
    assert session_b_id not in sess_ids_a

    # Trainer B lists sessions: sees Session B, never Session A
    sessions_b = client.get("/api/sessions", headers=headers_b).json()
    sess_ids_b = [s["id"] for s in sessions_b]
    assert session_b_id in sess_ids_b
    assert session_a_id not in sess_ids_b

    # Trainer A cannot view Session B
    res_cross_get = client.get(f"/api/sessions/{session_b_id}", headers=headers_a)
    assert res_cross_get.status_code == 403

    # Trainer A cannot edit Session B
    res_cross_put = client.put(
        f"/api/sessions/{session_b_id}",
        json={"notes": "Hacked notes"},
        headers=headers_a,
    )
    assert res_cross_put.status_code in (403, 404)

    # Trainer A cannot complete Session B
    res_cross_complete = client.post(
        f"/api/sessions/{session_b_id}/complete",
        headers=headers_a,
    )
    assert res_cross_complete.status_code == 403

    # Trainer A cannot delete Session B
    res_cross_del = client.delete(f"/api/sessions/{session_b_id}", headers=headers_a)
    assert res_cross_del.status_code in (403, 404)


def test_daily_workout_session_tracking_requirements(client):
    """
    Verify:
    1. Trainer can record multiple sessions for the same client on different dates.
    2. Every session creates a separate persistent database record with exercises, sets, reps, kg.
    3. Sessions are organized reverse-chronologically by date.
    4. Rapid duplicate submissions within window are deduplicated.
    5. Previous sessions are never overwritten.
    """
    headers_a = _get_auth_header(client, "alice.trainer@testgym.com", "Password123!")
    client_a1 = client.get("/api/clients?search=Alice+Athlete", headers=headers_a).json()[0]
    exercises = client.get("/api/exercises", headers=headers_a).json()
    squat_id = next(e["id"] for e in exercises if "Squat" in e["name"])

    # Day 1: Session 2 days ago
    date_day1 = str(date.today() - timedelta(days=2))
    payload_day1 = {
        "client_id": client_a1["id"],
        "workout_name": "Leg Day Volume",
        "date": date_day1,
        "duration_minutes": 60,
        "notes": "Good depth on squats",
        "status": "COMPLETED",
        "exercises": [
            {"exercise_id": squat_id, "sets_completed": 4, "reps": 10, "weight_used": 100.0, "notes": "Felt strong"}
        ],
    }
    res1 = client.post("/api/sessions", json=payload_day1, headers=headers_a)
    assert res1.status_code == 201
    sess1_id = res1.json()["id"]

    # Day 2: Session yesterday
    date_day2 = str(date.today() - timedelta(days=1))
    payload_day2 = {
        "client_id": client_a1["id"],
        "workout_name": "Active Recovery",
        "date": date_day2,
        "duration_minutes": 45,
        "notes": "Mobility and light work",
        "status": "COMPLETED",
        "exercises": [
            {"exercise_id": squat_id, "sets_completed": 3, "reps": 12, "weight_used": 60.0}
        ],
    }
    res2 = client.post("/api/sessions", json=payload_day2, headers=headers_a)
    assert res2.status_code == 201
    sess2_id = res2.json()["id"]

    # Verify both records are distinct persistent records and Day 1 was not overwritten
    assert sess1_id != sess2_id
    sess1_check = client.get(f"/api/sessions/{sess1_id}", headers=headers_a).json()
    assert sess1_check["date"] == date_day1
    assert sess1_check["workout_name"] == "Leg Day Volume"
    assert len(sess1_check["exercises"]) == 1
    assert sess1_check["exercises"][0]["weight_used"] == 100.0

    # Rapid accidental duplicate submission check (same client, same date, same workout_name immediately)
    res2_dup = client.post("/api/sessions", json=payload_day2, headers=headers_a)
    assert res2_dup.status_code in (200, 201)
    # Deduplication returns existing session id without creating a duplicate row
    assert res2_dup.json()["id"] == sess2_id

    # Client history listing organized by date descending
    all_sess = client.get(f"/api/sessions?client_id={client_a1['id']}", headers=headers_a).json()
    dates = [s["date"] for s in all_sess]
    # Check that date_day2 appears before or equal to date_day1 (descending)
    idx2 = dates.index(date_day2)
    idx1 = dates.index(date_day1)
    assert idx2 < idx1


def test_trainer_notes_isolation_between_trainers(client):
    headers_a = _get_auth_header(client, "alice.trainer@testgym.com", "Password123!")
    headers_b = _get_auth_header(client, "bob.trainer@testgym.com", "Password123!")

    client_a1 = client.get("/api/clients?search=Alice+Athlete", headers=headers_a).json()[0]
    client_b1 = client.get("/api/clients?search=Bob+Athlete", headers=headers_b).json()[0]

    # Trainer A adds note for Client A1
    res_na = client.post(
        f"/api/notes/client/{client_a1['id']}",
        json={"note": "Private evaluation: Alice needs shoulder mobility work."},
        headers=headers_a,
    )
    assert res_na.status_code == 201
    note_a_id = res_na.json()["id"]

    # Trainer B attempts to read notes for Client A1: must be blocked with 403
    res_nb = client.get(f"/api/notes/client/{client_a1['id']}", headers=headers_b)
    assert res_nb.status_code == 403

    # Trainer B cannot update Trainer A's note
    res_edit = client.put(f"/api/notes/{note_a_id}", json={"note": "Compromised"}, headers=headers_b)
    assert res_edit.status_code in (403, 404)

    # Trainer B cannot delete Trainer A's note
    res_del = client.delete(f"/api/notes/{note_a_id}", headers=headers_b)
    assert res_del.status_code in (403, 404)


def test_trainer_dashboard_metrics_isolation(client):
    headers_a = _get_auth_header(client, "alice.trainer@testgym.com", "Password123!")
    headers_b = _get_auth_header(client, "bob.trainer@testgym.com", "Password123!")
    headers_c = _get_auth_header(client, "charlie.trainer@testgym.com", "Password123!")

    dash_a = client.get("/api/dashboard/trainer", headers=headers_a).json()
    dash_b = client.get("/api/dashboard/trainer", headers=headers_b).json()
    dash_c = client.get("/api/dashboard/trainer", headers=headers_c).json()

    # Trainer Charlie has no clients, attendance, fees or alerts
    assert dash_c["total_clients"] == 0
    assert dash_c["active_clients"] == 0
    assert dash_c["today_attendance"] == {"present": 0, "absent": 0, "late": 0, "unmarked": 0}
    assert dash_c["billing"]["outstanding_total"] == 0
    assert dash_c["billing"]["overdue_count"] == 0
    assert dash_c["billing"]["collected_this_month"] == 0
    assert dash_c["billing"]["unread_alerts"] == 0
    assert dash_c["upcoming_dues"] == []
    assert dash_c["recent_clients"] == []

    # Trainer Alice dashboard contains only Alice's records
    alice_client_names = [c["name"] for c in dash_a["recent_clients"]]
    assert "Alice Athlete One" in alice_client_names
    assert "Bob Athlete One" not in alice_client_names
    assert all("Bob Athlete" not in d["client_name"] for d in dash_a["upcoming_dues"])

    # Trainer Bob dashboard contains only Bob's records
    bob_client_names = [c["name"] for c in dash_b["recent_clients"]]
    assert "Bob Athlete One" in bob_client_names
    assert "Alice Athlete One" not in bob_client_names
    assert all("Alice Athlete" not in d["client_name"] for d in dash_b["upcoming_dues"])


def test_fee_isolation_between_trainers(client):
    headers_a = _get_auth_header(client, "alice.trainer@testgym.com", "Password123!")
    headers_b = _get_auth_header(client, "bob.trainer@testgym.com", "Password123!")

    client_a1 = client.get("/api/clients?search=Alice+Athlete", headers=headers_a).json()[0]
    client_b1 = client.get("/api/clients?search=Bob+Athlete", headers=headers_b).json()[0]

    # Alice bills her client
    plan_res = client.post(
        "/api/fees/plans", json={"name": "Alice Monthly", "price": "1000", "duration_months": 1}, headers=headers_a
    )
    assert plan_res.status_code == 201
    plan_a = plan_res.json()
    account = client.put(
        f"/api/fees/clients/{client_a1['id']}/membership", json={"plan_id": plan_a["id"]}, headers=headers_a
    )
    assert account.status_code == 200
    fee_a = account.json()["fees"][0]

    # Bob sees none of it
    assert plan_a["id"] not in [p["id"] for p in client.get("/api/fees/plans", headers=headers_b).json()]
    bob_fees = client.get("/api/fees", params={"page_size": 100}, headers=headers_b).json()["items"]
    assert fee_a["id"] not in [f["id"] for f in bob_fees]
    bob_members = client.get("/api/fees/memberships", params={"page_size": 100}, headers=headers_b).json()["items"]
    assert client_a1["id"] not in [m["client_id"] for m in bob_members]
    assert client.get(f"/api/fees/clients/{client_a1['id']}", headers=headers_b).status_code == 403

    # Bob cannot change Alice's plans, memberships, fees or payments
    assert client.put(f"/api/fees/plans/{plan_a['id']}", json={"price": "1"}, headers=headers_b).status_code in (403, 404)
    assert client.delete(f"/api/fees/plans/{plan_a['id']}", headers=headers_b).status_code in (403, 404)
    assert client.put(
        f"/api/fees/clients/{client_b1['id']}/membership", json={"plan_id": plan_a["id"]}, headers=headers_b
    ).status_code == 404
    assert client.delete(f"/api/fees/clients/{client_a1['id']}/membership", headers=headers_b).status_code in (403, 404)
    assert client.post(f"/api/fees/{fee_a['id']}/payments", json={"amount": "10"}, headers=headers_b).status_code == 404
    assert client.patch(f"/api/fees/{fee_a['id']}", json={"is_waived": True}, headers=headers_b).status_code == 404
    assert client.delete(f"/api/fees/{fee_a['id']}", headers=headers_b).status_code == 404

    paid = client.post(f"/api/fees/{fee_a['id']}/payments", json={"amount": "100"}, headers=headers_a)
    assert paid.status_code == 201
    payment_id = paid.json()["payments"][0]["id"]
    assert client.delete(f"/api/fees/payments/{payment_id}", headers=headers_b).status_code == 404

    # Alice's records are intact
    after = client.get(f"/api/fees/clients/{client_a1['id']}", headers=headers_a).json()
    fee_after = next(f for f in after["fees"] if f["id"] == fee_a["id"])
    assert fee_after["amount_paid"] == 100.0 and fee_after["is_waived"] is False
    assert after["membership"]["plan_id"] == plan_a["id"]


def test_select_exercises_for_a_day(client):
    headers_a = _get_auth_header(client, "alice.trainer@testgym.com", "Password123!")
    headers_b = _get_auth_header(client, "bob.trainer@testgym.com", "Password123!")
    client_a1 = client.get("/api/clients?search=Alice+Athlete", headers=headers_a).json()[0]
    exercises = client.get("/api/exercises", headers=headers_a).json()
    ex_ids = [e["id"] for e in exercises[:3]]
    day = str(date.today() - timedelta(days=10))

    # Tick two exercises: one record for the day, no sets/reps needed
    res = client.put(
        "/api/sessions/day",
        json={"client_id": client_a1["id"], "date": day, "exercise_ids": ex_ids[:2]},
        headers=headers_a,
    )
    assert res.status_code == 200, res.text
    sess = res.json()
    assert sess["date"] == day
    assert [e["exercise_id"] for e in sess["exercises"]] == ex_ids[:2]
    assert all(e["sets_completed"] is None and e["reps"] is None for e in sess["exercises"])
    assert sess["workout_name"]

    # Saving again for the same day updates the same record
    res2 = client.put(
        "/api/sessions/day",
        json={"client_id": client_a1["id"], "date": day, "exercise_ids": ex_ids[1:3]},
        headers=headers_a,
    )
    assert res2.status_code == 200
    assert res2.json()["id"] == sess["id"]
    assert sorted(e["exercise_id"] for e in res2.json()["exercises"]) == sorted(ex_ids[1:3])
    day_list = client.get(
        f"/api/sessions?client_id={client_a1['id']}&session_date={day}", headers=headers_a
    ).json()
    assert len(day_list) == 1

    # Unknown exercise is rejected
    bad = client.put(
        "/api/sessions/day",
        json={"client_id": client_a1["id"], "date": day, "exercise_ids": [999999]},
        headers=headers_a,
    )
    assert bad.status_code == 400

    # Another trainer cannot write to this client's day
    cross = client.put(
        "/api/sessions/day",
        json={"client_id": client_a1["id"], "date": day, "exercise_ids": ex_ids[:1]},
        headers=headers_b,
    )
    assert cross.status_code in (403, 404)

    # Clearing every exercise removes the day's record
    cleared = client.put(
        "/api/sessions/day",
        json={"client_id": client_a1["id"], "date": day, "exercise_ids": []},
        headers=headers_a,
    )
    assert cleared.status_code == 200 and cleared.json() is None
    assert client.get(
        f"/api/sessions?client_id={client_a1['id']}&session_date={day}", headers=headers_a
    ).json() == []
