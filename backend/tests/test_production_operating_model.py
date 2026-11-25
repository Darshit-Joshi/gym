import pytest
from datetime import date


def test_setup_status_endpoint(client):
    res = client.get("/api/auth/setup-status")
    assert res.status_code == 200
    data = res.json()
    assert "is_setup_completed" in data
    assert "has_trainer" in data
    assert "can_register_trainer" in data


def test_multiple_trainer_setup_allowed(client):
    # Multiple independent trainers can register their own accounts
    res = client.post(
        "/api/auth/setup-trainer",
        json={
            "name": "Second Independent Trainer",
            "email": "trainer2_allowed@example.com",
            "password": "SecurePassword123!",
            "phone": "+1-555-9999",
        },
    )
    assert res.status_code == 201
    assert res.json()["role"] == "TRAINER"


def test_client_onboarding_without_login(client, trainer_auth_headers):
    headers = trainer_auth_headers

    # 1. With an email: active immediately, no activation artefacts
    res = client.post(
        "/api/clients",
        json={
            "name": "Ananya Roy",
            "email": "Ananya.Roy@Example.com",
            "phone": "9876500001",
            "fitness_goal": "Weight Loss",
            "gender": "Female",
            "age": 26,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["status"] == "Active"
    assert data["email"] == "ananya.roy@example.com"
    assert "activation_token" not in data
    assert "activation_link" not in data
    assert "password" not in data

    # Duplicate email is still rejected
    dup = client.post("/api/clients", json={"name": "Ananya Again", "email": "ananya.roy@example.com"}, headers=headers)
    assert dup.status_code == 400


def test_client_creation_without_email(client, trainer_auth_headers):
    headers = trainer_auth_headers

    # Email omitted
    res1 = client.post("/api/clients", json={"name": "No Email One", "phone": "9876500011"}, headers=headers)
    assert res1.status_code == 201, res1.text
    c1 = res1.json()
    assert c1["email"] is None
    assert c1["status"] == "Active"

    # A second client without email does not collide with the first
    res2 = client.post("/api/clients", json={"name": "No Email Two"}, headers=headers)
    assert res2.status_code == 201, res2.text
    c2 = res2.json()
    assert c2["email"] is None
    assert c2["id"] != c1["id"]

    # Blank email is treated as no email
    res3 = client.post("/api/clients", json={"name": "No Email Three", "email": "   "}, headers=headers)
    assert res3.status_code == 201, res3.text
    assert res3.json()["email"] is None

    # Invalid email is still validated
    res_bad = client.post("/api/clients", json={"name": "Bad Email", "email": "not-an-email"}, headers=headers)
    assert res_bad.status_code == 422

    # Read back and list: email stays null
    assert client.get(f"/api/clients/{c1['id']}", headers=headers).json()["email"] is None
    listed = {c["id"]: c for c in client.get("/api/clients?search=No Email", headers=headers).json()}
    assert {c1["id"], c2["id"], res3.json()["id"]} <= set(listed)
    assert all(listed[i]["email"] is None for i in (c1["id"], c2["id"]))

    # Updating a no-email client works
    up = client.put(f"/api/clients/{c1['id']}", json={"current_weight": 70.5}, headers=headers)
    assert up.status_code == 200
    assert up.json()["current_weight"] == 70.5
    assert up.json()["email"] is None


def test_clients_pagination_and_goal_filtering(client, trainer_auth_headers):
    headers = trainer_auth_headers

    # Query with page=1 & page_size=2
    paginated_res = client.get("/api/clients?page=1&page_size=2", headers=headers)
    assert paginated_res.status_code == 200
    pdata = paginated_res.json()
    assert "items" in pdata
    assert "total" in pdata
    assert "page" in pdata
    assert "page_size" in pdata
    assert "total_pages" in pdata
    assert pdata["page"] == 1
    assert pdata["page_size"] == 2
    assert len(pdata["items"]) <= 2
    assert pdata["total"] >= 3

    # Query with goal filter
    goal_res = client.get("/api/clients?goal=Muscle Gain", headers=headers)
    assert goal_res.status_code == 200
    goal_clients = goal_res.json()
    assert isinstance(goal_clients, list)
    assert len(goal_clients) >= 1
    assert all("muscle gain" in c["fitness_goal"].lower() for c in goal_clients)


def test_archive_and_restore_client(client, trainer_auth_headers):
    headers = trainer_auth_headers

    # Search for Rahul
    rahul_res = client.get("/api/clients?search=Rahul", headers=headers)
    rahul = rahul_res.json()[0]

    # Archive Rahul (preserves workout history)
    archive_res = client.post(f"/api/clients/{rahul['id']}/archive", headers=headers)
    assert archive_res.status_code == 200

    # Verify status is Archived
    check_res = client.get(f"/api/clients/{rahul['id']}", headers=headers)
    assert check_res.json()["status"] == "Archived"

    # Restore Rahul to Active
    restore_res = client.put(
        f"/api/clients/{rahul['id']}",
        json={"status": "Active"},
        headers=headers,
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["status"] == "Active"


def test_update_profile_endpoint(client, trainer_auth_headers):
    headers = trainer_auth_headers

    # Update trainer profile phone
    up_res = client.put(
        "/api/auth/profile",
        json={"phone": "+1-555-9876"},
        headers=headers,
    )
    assert up_res.status_code == 200
    assert up_res.json()["phone"] == "+1-555-9876"


def test_search_never_matches_placeholder_emails(client, trainer_auth_headers):
    headers = trainer_auth_headers
    res = client.post("/api/clients", json={"name": "Search Probe NoMail"}, headers=headers)
    assert res.status_code == 201, res.text
    probe_id = res.json()["id"]

    for term in ("no-login", "invalid", "client-"):
        found = client.get("/api/clients", params={"search": term}, headers=headers).json()
        assert probe_id not in [c["id"] for c in found], f"search '{term}' matched a hidden placeholder email"

    # Searching by name still finds the client
    found = client.get("/api/clients", params={"search": "Search Probe"}, headers=headers).json()
    assert probe_id in [c["id"] for c in found]
