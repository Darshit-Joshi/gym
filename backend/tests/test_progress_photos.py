import io
from datetime import date, timedelta

from PIL import Image


def _auth(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _register(client, name, email, password="Password123!"):
    client.post(
        "/api/auth/register-trainer",
        json={"name": name, "email": email, "password": password, "phone": "+1-555-3000"},
    )
    return _auth(client, email, password)


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (40, 60), color=(20, 120, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _upload(client, headers, client_id, photo_date, category="FRONT", weight=None, notes=None, data=None):
    form = {"client_id": str(client_id), "photo_date": str(photo_date), "category": category}
    if weight is not None:
        form["weight"] = str(weight)
    if notes is not None:
        form["notes"] = notes
    return client.post(
        "/api/progress-photos",
        data=form,
        files={"file": ("week.png", data if data is not None else _png(), "image/png")},
        headers=headers,
    )


def test_weekly_progress_photos_lifecycle(client):
    headers = _register(client, "Photo Trainer", "photo.trainer@testgym.com")
    other = _register(client, "Other Photo Trainer", "photo.other@testgym.com")

    c = client.post(
        "/api/clients", json={"name": "Weekly Photo Client", "current_weight": 90}, headers=headers
    ).json()

    today = date.today()
    week1 = today - timedelta(days=14)

    # Upload two weeks of photos; weight on the newest becomes current weight
    r1 = _upload(client, headers, c["id"], week1, "FRONT", weight=88.5, notes="Start")
    assert r1.status_code == 201, r1.text
    p1 = r1.json()
    assert p1["week_start"] == str(week1 - timedelta(days=week1.weekday()))
    assert p1["weight"] == 88.5 and p1["category"] == "FRONT"

    r2 = _upload(client, headers, c["id"], today, "side", weight=86.0)
    assert r2.status_code == 201, r2.text
    p2 = r2.json()
    assert p2["category"] == "SIDE"
    assert client.get(f"/api/clients/{c['id']}", headers=headers).json()["current_weight"] == 86.0

    # An older photo with a weight does not overwrite the current weight
    r_old = _upload(client, headers, c["id"], today - timedelta(days=30), weight=95.0)
    assert r_old.status_code == 201
    assert client.get(f"/api/clients/{c['id']}", headers=headers).json()["current_weight"] == 86.0

    # Listed newest first
    listed = client.get(f"/api/progress-photos?client_id={c['id']}", headers=headers).json()
    assert [p["id"] for p in listed][:2] == [p2["id"], p1["id"]]

    # Image streams with a header token and with a ?token= query (for <img> tags)
    img = client.get(p1["image_url"], headers=headers)
    assert img.status_code == 200 and img.headers["content-type"].startswith("image/")
    token = headers["Authorization"].split()[1]
    assert client.get(f"{p1['image_url']}?token={token}").status_code == 200

    # Validation: future date, bad pose, non-image file
    assert _upload(client, headers, c["id"], today + timedelta(days=1)).status_code == 400
    assert _upload(client, headers, c["id"], today, "UPSIDE_DOWN").status_code == 422
    assert _upload(client, headers, c["id"], today, data=b"not an image").status_code == 400

    # Edit
    edited = client.patch(
        f"/api/progress-photos/{p1['id']}", json={"category": "BACK", "notes": "Edited"}, headers=headers
    )
    assert edited.status_code == 200
    assert edited.json()["category"] == "BACK" and edited.json()["notes"] == "Edited"

    # Another trainer can't list, view, edit or delete these photos
    assert client.get(f"/api/progress-photos?client_id={c['id']}", headers=other).status_code == 403
    assert client.get(p1["image_url"], headers=other).status_code == 404
    assert client.patch(f"/api/progress-photos/{p1['id']}", json={"notes": "x"}, headers=other).status_code == 404
    assert client.delete(f"/api/progress-photos/{p1['id']}", headers=other).status_code == 404

    # Delete removes the record and the image
    assert client.delete(f"/api/progress-photos/{p1['id']}", headers=headers).status_code == 200
    assert client.get(p1["image_url"], headers=headers).status_code == 404
    remaining = client.get(f"/api/progress-photos?client_id={c['id']}", headers=headers).json()
    assert p1["id"] not in [p["id"] for p in remaining]
    for p in remaining:
        client.delete(f"/api/progress-photos/{p['id']}", headers=headers)
