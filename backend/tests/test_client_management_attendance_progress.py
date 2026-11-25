import io
import pytest
from PIL import Image


def _get_auth_header(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_sample_image(format="PNG"):
    img = Image.new("RGB", (32, 32), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def trainer_t1(client):
    email = "test_trainer_t1@gymtest.com"
    pwd = "TrainerPassword123!"
    res = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Trainer T1",
            "email": email,
            "password": pwd,
            "phone": "+1-555-8881",
        },
    )
    if res.status_code != 201:
        # Might already exist in test run
        pass
    return email, pwd


@pytest.fixture
def trainer_t2(client):
    email = "test_trainer_t2@gymtest.com"
    pwd = "TrainerPassword123!"
    res = client.post(
        "/api/auth/register-trainer",
        json={
            "name": "Trainer T2",
            "email": email,
            "password": pwd,
            "phone": "+1-555-8882",
        },
    )
    if res.status_code != 201:
        pass
    return email, pwd


def test_client_profile_creation_with_extra_fields(client, trainer_t1):
    email, pwd = trainer_t1
    headers = _get_auth_header(client, email, pwd)

    res = client.post(
        "/api/clients",
        json={
            "name": "Jordan Henderson",
            "email": "jordan.h@example.com",
            "phone": "+1-555-0909",
            "fitness_goal": "Strength",
            "gender": "Male",
            "age": 31,
            "emergency_contact": "Jane Henderson (+1-555-9999)",
            "joined_date": "2026-10-01",
            "training_preferences": "Morning sessions, knee injury caution",
        },
        headers=headers,
    )
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == "Jordan Henderson"
    assert created["emergency_contact"] == "Jane Henderson (+1-555-9999)"
    assert created["joined_date"] == "2026-10-01"
    assert created["training_preferences"] == "Morning sessions, knee injury caution"

    # Verify retrieval
    res_get = client.get(f"/api/clients/{created['id']}", headers=headers)
    assert res_get.status_code == 200
    retrieved = res_get.json()
    assert retrieved["emergency_contact"] == "Jane Henderson (+1-555-9999)"
    assert retrieved["joined_date"] == "2026-10-01"


def test_client_profile_photo_upload_retrieve_delete(client, trainer_t1):
    email, pwd = trainer_t1
    headers = _get_auth_header(client, email, pwd)

    # 1. Create client
    res_c = client.post(
        "/api/clients",
        json={
            "name": "Sarah Connor",
            "email": "sarah.c@example.com",
            "phone": "+1-555-0707",
            "fitness_goal": "Endurance",
            "gender": "Female",
            "age": 35,
        },
        headers=headers,
    )
    assert res_c.status_code == 201
    c_id = res_c.json()["id"]

    # 2. Upload valid image
    img_bytes = _create_sample_image("PNG")
    files = {"file": ("avatar.png", img_bytes, "image/png")}
    res_up = client.post(f"/api/clients/{c_id}/photo", files=files, headers=headers)
    assert res_up.status_code == 200, res_up.text
    up_data = res_up.json()
    assert up_data["profile_photo"] is not None
    assert "photo_url" in up_data

    # 3. Retrieve image stream
    res_stream = client.get(f"/api/clients/{c_id}/photo", headers=headers)
    assert res_stream.status_code == 200
    assert "image" in res_stream.headers.get("content-type", "")
    assert len(res_stream.content) > 0

    # 4. Reject invalid non-image file
    bad_files = {"file": ("malicious.txt", b"not an image text content", "text/plain")}
    res_bad = client.post(f"/api/clients/{c_id}/photo", files=bad_files, headers=headers)
    assert res_bad.status_code == 400

    # 5. Delete profile photo
    res_del = client.delete(f"/api/clients/{c_id}/photo", headers=headers)
    assert res_del.status_code == 200

    # 6. Verify subsequent photo GET returns 404
    res_stream_after = client.get(f"/api/clients/{c_id}/photo", headers=headers)
    assert res_stream_after.status_code == 404


def test_daily_attendance_workflow_and_upsert(client, trainer_t1):
    email, pwd = trainer_t1
    headers = _get_auth_header(client, email, pwd)

    # 1. Create client
    res_c = client.post(
        "/api/clients",
        json={
            "name": "Marcus Aurelius",
            "email": "marcus.aurelius@example.com",
            "phone": "+1-555-0808",
            "fitness_goal": "General Fitness",
        },
        headers=headers,
    )
    assert res_c.status_code == 201
    c_id = res_c.json()["id"]

    test_date = "2026-10-15"

    # 2. Check daily sheet initially
    res_sheet = client.get(f"/api/attendance?attendance_date={test_date}", headers=headers)
    assert res_sheet.status_code == 200
    sheet_data = res_sheet.json()
    item = next((i for i in sheet_data["clients"] if i["client_id"] == c_id), None)
    assert item is not None
    assert item["status"] is None  # unmarked

    # 3. Record attendance as PRESENT
    res_rec1 = client.post(
        "/api/attendance",
        json={
            "client_id": c_id,
            "date": test_date,
            "status": "PRESENT",
            "notes": "On time and energetic",
        },
        headers=headers,
    )
    assert res_rec1.status_code in (200, 201)

    # Verify sheet updated
    res_sheet2 = client.get(f"/api/attendance?attendance_date={test_date}", headers=headers)
    item2 = next((i for i in res_sheet2.json()["clients"] if i["client_id"] == c_id), None)
    assert item2["status"] == "PRESENT"
    assert res_sheet2.json()["present_count"] >= 1

    # 4. Upsert check: Submit attendance again for SAME client + SAME date with LATE
    res_rec2 = client.post(
        "/api/attendance",
        json={
            "client_id": c_id,
            "date": test_date,
            "status": "LATE",
            "notes": "Arrived 15 mins late due to traffic",
        },
        headers=headers,
    )
    assert res_rec2.status_code in (200, 201)

    # 5. Verify client attendance history has only ONE entry for that date (no duplicates)
    res_hist = client.get(f"/api/attendance/client/{c_id}", headers=headers)
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert hist_data["total_recorded"] == 1
    assert hist_data["late_count"] == 1
    assert hist_data["present_count"] == 0
    assert hist_data["attendance_percentage"] == 100.0  # LATE counts as attended

def test_attendance_timestamp_weekday_and_modification_integrity(client, trainer_t1):
    email, pwd = trainer_t1
    headers = _get_auth_header(client, email, pwd)

    # 1. Create client
    res_c = client.post(
        "/api/clients",
        json={
            "name": "Timestamp Verification Athlete",
            "email": "timestamp.athlete@example.com",
            "phone": "+1-555-7777",
            "fitness_goal": "Strength",
        },
        headers=headers,
    )
    assert res_c.status_code == 201
    c_id = res_c.json()["id"]

    # Date: Sunday, 11 October 2026
    test_date = "2026-10-11"

    # 2. Daily sheet initially shows day_name and formatted_date
    res_sheet = client.get(f"/api/attendance?attendance_date={test_date}", headers=headers)
    assert res_sheet.status_code == 200
    sheet = res_sheet.json()
    assert sheet["day_name"] == "Sunday"
    assert "11 October 2026" in sheet["formatted_date"]

    # 3. Record attendance
    res_mark = client.post(
        "/api/attendance",
        json={
            "client_id": c_id,
            "date": test_date,
            "status": "PRESENT",
            "notes": "Morning training session",
        },
        headers=headers,
    )
    assert res_mark.status_code == 200
    marked = res_mark.json()
    assert marked["day_name"] == "Sunday"
    assert marked["formatted_date"] == "11 October 2026"
    assert marked["attendance_time"] is not None
    assert marked["recorded_by_name"] == email
    orig_created_at = marked["created_at"]
    orig_att_time = marked["attendance_time"]

    # 4. Upsert/modify record with different status and note
    res_mod = client.post(
        "/api/attendance",
        json={
            "client_id": c_id,
            "date": test_date,
            "status": "LATE",
            "notes": "Traffic delay but completed full workout",
        },
        headers=headers,
    )
    assert res_mod.status_code == 200
    modified = res_mod.json()
    # Check that original created_at timestamp is strictly preserved
    assert modified["created_at"] == orig_created_at
    assert modified["attendance_time"] == orig_att_time
    assert modified["status"] == "LATE"
    assert modified["recorded_by_name"] == email
    assert modified["last_modified_by_name"] == email
    assert modified["last_modified_time"] is not None

    # 5. Add another record on a different date: 2026-10-12 (Monday)
    res_mark2 = client.post(
        "/api/attendance",
        json={
            "client_id": c_id,
            "date": "2026-10-12",
            "status": "PRESENT",
            "notes": "Back on schedule",
        },
        headers=headers,
    )
    assert res_mark2.status_code == 200
    assert res_mark2.json()["day_name"] == "Monday"

    # 6. Test filters in get_client_attendance_history
    # Filter by exact date
    res_filt_date = client.get(f"/api/attendance/client/{c_id}?date={test_date}", headers=headers)
    assert res_filt_date.status_code == 200
    assert len(res_filt_date.json()["records"]) == 1
    assert res_filt_date.json()["records"][0]["date"] == test_date

    # Filter by month
    res_filt_mo = client.get(f"/api/attendance/client/{c_id}?month=2026-10", headers=headers)
    assert res_filt_mo.status_code == 200
    assert len(res_filt_mo.json()["records"]) == 2

    # Filter by status
    res_filt_late = client.get(f"/api/attendance/client/{c_id}?status=LATE", headers=headers)
    assert res_filt_late.status_code == 200
    assert len(res_filt_late.json()["records"]) == 1
    assert res_filt_late.json()["records"][0]["status"] == "LATE"

    # Invalid month returns 400
    res_bad_mo = client.get(f"/api/attendance/client/{c_id}?month=invalid-month", headers=headers)
    assert res_bad_mo.status_code == 400



def test_multi_trainer_isolation_photos_and_attendance(client, trainer_t1, trainer_t2):
    email1, pwd1 = trainer_t1
    email2, pwd2 = trainer_t2

    headers1 = _get_auth_header(client, email1, pwd1)
    headers2 = _get_auth_header(client, email2, pwd2)

    # Trainer 1 creates Client Alpha
    res_ca = client.post(
        "/api/clients",
        json={"name": "Client Alpha (Trainer 1)", "email": "alpha.client@test.com"},
        headers=headers1,
    )
    assert res_ca.status_code == 201
    c_alpha_id = res_ca.json()["id"]

    # Trainer 1 uploads profile photo
    img_bytes = _create_sample_image("PNG")
    res_up = client.post(
        f"/api/clients/{c_alpha_id}/photo",
        files={"file": ("alpha.png", img_bytes, "image/png")},
        headers=headers1,
    )
    assert res_up.status_code == 200

    # Trainer 1 marks attendance
    res_att = client.post(
        "/api/attendance",
        json={"client_id": c_alpha_id, "date": "2026-10-14", "status": "PRESENT"},
        headers=headers1,
    )
    assert res_att.status_code == 200

    # -------------------------------------------------------------
    # NOW TEST TRAINER 2 STRICT ISOLATION AGAINST CLIENT ALPHA DATA
    # -------------------------------------------------------------

    # 1. Trainer 2 cannot stream Trainer 1 client's profile photo
    res_p_stream = client.get(f"/api/clients/{c_alpha_id}/photo", headers=headers2)
    assert res_p_stream.status_code in (403, 404)

    # 2. Trainer 2 cannot view Trainer 1 client's attendance history
    res_att_hist = client.get(f"/api/attendance/client/{c_alpha_id}", headers=headers2)
    assert res_att_hist.status_code in (403, 404)

    # 3. Trainer 2 cannot mark attendance for Trainer 1's client
    res_att_mark = client.post(
        "/api/attendance",
        json={"client_id": c_alpha_id, "date": "2026-10-14", "status": "PRESENT"},
        headers=headers2,
    )
    assert res_att_mark.status_code in (403, 404)

    # 4. Trainer 2 cannot see Trainer 1's client on Trainer 2's daily attendance sheet
    res_att_sheet = client.get("/api/attendance?attendance_date=2026-10-14", headers=headers2)
    assert res_att_sheet.status_code == 200
    trainer2_sheet_clients = [i["client_id"] for i in res_att_sheet.json()["clients"]]
    assert c_alpha_id not in trainer2_sheet_clients

    # 5. Trainer 2 cannot upload a photo for Trainer 1's client
    res_p_up = client.post(
        f"/api/clients/{c_alpha_id}/photo",
        files={"file": ("x.png", img_bytes, "image/png")},
        headers=headers2,
    )
    assert res_p_up.status_code in (403, 404)


def test_media_streaming_with_query_token(client, trainer_t1):
    email, pwd = trainer_t1
    res_login = client.post("/api/auth/login", json={"email": email, "password": pwd})
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create client
    res_c = client.post(
        "/api/clients",
        json={"name": "Media Token Athlete", "email": "media.token@athlete.com"},
        headers=headers,
    )
    c_id = res_c.json()["id"]

    # Upload photo
    img_bytes = _create_sample_image("PNG")
    client.post(
        f"/api/clients/{c_id}/photo",
        files={"file": ("token_avatar.png", img_bytes, "image/png")},
        headers=headers,
    )

    # 1. Access WITHOUT headers or token param -> 401
    res_no_token = client.get(f"/api/clients/{c_id}/photo")
    assert res_no_token.status_code == 401

    # 2. Access with token QUERY PARAMETER (as browser <img> tags do) -> 200
    res_query_token = client.get(f"/api/clients/{c_id}/photo?token={token}")
    assert res_query_token.status_code == 200
    assert "image" in res_query_token.headers.get("content-type", "")
    assert len(res_query_token.content) > 0


def test_monthly_attendance_overview_and_calendar_isolation(client, trainer_t1, trainer_t2):
    t1_email, t1_pwd = trainer_t1
    t2_email, t2_pwd = trainer_t2
    headers1 = _get_auth_header(client, t1_email, t1_pwd)
    headers2 = _get_auth_header(client, t2_email, t2_pwd)

    # 1. Trainer 1 creates client A
    res_a = client.post(
        "/api/clients",
        json={"name": "Monthly Athlete One", "email": "monthly.athlete.one@gymtest.com"},
        headers=headers1,
    )
    assert res_a.status_code == 201
    client_a_id = res_a.json()["id"]

    # 2. Trainer 2 creates client B
    res_b = client.post(
        "/api/clients",
        json={"name": "Monthly Athlete Two", "email": "monthly.athlete.two@gymtest.com"},
        headers=headers2,
    )
    assert res_b.status_code == 201
    client_b_id = res_b.json()["id"]

    # 3. Trainer 1 logs attendance for Athlete One across 3 days in October 2026
    for dt, st in [("2026-10-01", "PRESENT"), ("2026-10-02", "LATE"), ("2026-10-03", "ABSENT")]:
        res_att = client.post(
            "/api/attendance",
            json={"client_id": client_a_id, "date": dt, "status": st, "notes": f"Note for {dt}"},
            headers=headers1,
        )
        assert res_att.status_code == 200

    # 4. Trainer 2 logs attendance for Athlete Two
    res_att_b = client.post(
        "/api/attendance",
        json={"client_id": client_b_id, "date": "2026-10-01", "status": "PRESENT"},
        headers=headers2,
    )
    assert res_att_b.status_code == 200

    # 5. Trainer 1 queries monthly overview for 2026-10
    res_over1 = client.get("/api/attendance/monthly-overview?month=2026-10", headers=headers1)
    assert res_over1.status_code == 200
    data1 = res_over1.json()
    assert data1["month"] == "2026-10"
    assert "October 2026" in data1["month_name"]

    # Check client A is present in Trainer 1's overview
    client_a_overview = next((c for c in data1["clients"] if c["client_id"] == client_a_id), None)
    assert client_a_overview is not None
    assert client_a_overview["present_count"] == 1
    assert client_a_overview["late_count"] == 1
    assert client_a_overview["absent_count"] == 1
    assert client_a_overview["total_recorded"] == 3
    # Attendance rate: (1 + 1) / 3 * 100 = 66.7%
    assert client_a_overview["attendance_percentage"] == 66.7

    # Ensure Trainer 2's client B is NOT in Trainer 1's overview (data isolation)
    assert not any(c["client_id"] == client_b_id for c in data1["clients"])

    # 6. Trainer 2 queries monthly overview for 2026-10
    res_over2 = client.get("/api/attendance/monthly-overview?month=2026-10", headers=headers2)
    assert res_over2.status_code == 200
    data2 = res_over2.json()
    # Ensure Trainer 1's client A is NOT in Trainer 2's overview
    assert not any(c["client_id"] == client_a_id for c in data2["clients"])
    # Client B is in Trainer 2's overview
    client_b_overview = next((c for c in data2["clients"] if c["client_id"] == client_b_id), None)
    assert client_b_overview is not None
    assert client_b_overview["present_count"] == 1
    assert client_b_overview["attendance_percentage"] == 100.0

    # 7. Trainer 1 gets individual client monthly attendance
    res_cal = client.get(f"/api/attendance/client/{client_a_id}?month=2026-10", headers=headers1)
    assert res_cal.status_code == 200
    cal_data = res_cal.json()
    assert cal_data["total_recorded"] == 3
    assert cal_data["present_count"] == 1
    assert cal_data["late_count"] == 1
    assert cal_data["absent_count"] == 1
    assert cal_data["attendance_percentage"] == 66.7
    assert len(cal_data["records"]) == 3

    # 8. Trainer 2 cannot access Trainer 1's client attendance calendar
    res_cal_unauth = client.get(f"/api/attendance/client/{client_a_id}?month=2026-10", headers=headers2)
    assert res_cal_unauth.status_code in (403, 404)

    # 9. Search filter in monthly overview
    res_search = client.get("/api/attendance/monthly-overview?month=2026-10&search=Monthly Athlete One", headers=headers1)
    assert res_search.status_code == 200
    search_clients = res_search.json()["clients"]
    assert len(search_clients) == 1
    assert search_clients[0]["client_id"] == client_a_id

