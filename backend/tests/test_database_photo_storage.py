"""Photos stored in the app's database (STORAGE_BACKEND=database) and the database-size warning."""
import io
from datetime import date

import pytest
from PIL import Image

from app.core.config import settings
from app.models.notification import Notification
from app.models.stored_file import StoredFile
from app.models.trainer import Trainer
from app.services.storage_usage import check_database_size


def _jpeg(size=(2400, 3200)):
    buf = io.BytesIO()
    Image.new("RGB", size, color=(30, 140, 90)).save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture
def database_storage(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "database")


@pytest.fixture(scope="module")
def headers(client):
    email, password = "db.storage.trainer@testgym.com", "Password123!"
    client.post(
        "/api/auth/register-trainer",
        json={"name": "DB Storage Trainer", "email": email, "password": password},
    )
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _stored(db_session, key):
    db_session.expire_all()
    return db_session.query(StoredFile).filter(StoredFile.key == key).first()


def test_profile_photo_lifecycle_in_database(client, headers, db_session, database_storage):
    c = client.post("/api/clients", json={"name": "DB Photo Client"}, headers=headers).json()

    up = client.post(
        f"/api/clients/{c['id']}/photo", files={"file": ("me.jpg", _jpeg(), "image/jpeg")}, headers=headers
    )
    assert up.status_code == 200, up.text
    key = up.json()["profile_photo"]
    row = _stored(db_session, key)
    assert row is not None and row.content_type == "image/jpeg" and row.size_bytes == len(row.data)

    img = client.get(f"/api/clients/{c['id']}/photo", headers=headers)
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/jpeg"
    assert img.headers["cache-control"].startswith("private")
    assert max(Image.open(io.BytesIO(img.content)).size) == 800

    # Replacing removes the old photo; deleting removes the new one
    up2 = client.post(
        f"/api/clients/{c['id']}/photo", files={"file": ("me2.jpg", _jpeg(), "image/jpeg")}, headers=headers
    )
    key2 = up2.json()["profile_photo"]
    assert _stored(db_session, key) is None and _stored(db_session, key2) is not None

    assert client.delete(f"/api/clients/{c['id']}/photo", headers=headers).status_code == 200
    assert _stored(db_session, key2) is None
    assert client.get(f"/api/clients/{c['id']}/photo", headers=headers).status_code == 404


def test_progress_photo_in_database_is_resized_and_deleted(client, headers, db_session, database_storage):
    c = client.post("/api/clients", json={"name": "DB Progress Client"}, headers=headers).json()
    res = client.post(
        "/api/progress-photos",
        data={"client_id": str(c["id"]), "photo_date": str(date.today()), "category": "FRONT"},
        files={"file": ("week.jpg", _jpeg(), "image/jpeg")},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    photo = res.json()

    token = headers["Authorization"].split()[1]
    img = client.get(f"{photo['image_url']}?token={token}")
    assert img.status_code == 200
    assert max(Image.open(io.BytesIO(img.content)).size) == 1280

    key = db_session.query(StoredFile.key).order_by(StoredFile.created_at.desc()).first()[0]
    assert client.delete(f"/api/progress-photos/{photo['id']}", headers=headers).status_code == 200
    assert _stored(db_session, key) is None


def test_permanent_client_delete_removes_their_photos(client, headers, db_session, database_storage):
    c = client.post("/api/clients", json={"name": "DB Leaving Client"}, headers=headers).json()
    key = client.post(
        f"/api/clients/{c['id']}/photo", files={"file": ("me.jpg", _jpeg(), "image/jpeg")}, headers=headers
    ).json()["profile_photo"]
    assert client.post(f"/api/clients/{c['id']}/archive", headers=headers).status_code == 200
    assert client.delete(f"/api/clients/{c['id']}/permanent", headers=headers).status_code == 200
    assert _stored(db_session, key) is None


# ---------------------------------------------------------------- size warning

def test_database_size_warning_levels_and_dedupe(db_session, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_SIZE_LIMIT_MB", 500)
    trainers = db_session.query(Trainer).filter(Trainer.user_id.isnot(None)).all()
    assert trainers
    today = date(2026, 11, 25)

    def alerts():
        return db_session.query(Notification).filter(Notification.type == "STORAGE_LOW").all()

    assert check_database_size(db_session, trainers, today, size_mb=300) == 0
    assert alerts() == []

    assert check_database_size(db_session, trainers, today, size_mb=410) == len(trainers)
    assert check_database_size(db_session, trainers, today, size_mb=420) == 0  # once per month
    first = alerts()
    assert {a.severity for a in first} == {"WARNING"}
    assert first[0].title == "Database 82% full" and first[0].client_id is None

    assert check_database_size(db_session, trainers, today, size_mb=480) == len(trainers)
    assert "CRITICAL" in {a.severity for a in alerts()}

    # Clean up so other tests' notification counts are unaffected
    for a in alerts():
        db_session.delete(a)
    db_session.commit()


def test_database_size_check_off_by_default_and_skipped_on_sqlite(db_session, monkeypatch):
    trainers = db_session.query(Trainer).all()
    monkeypatch.setattr(settings, "DATABASE_SIZE_LIMIT_MB", 0)
    assert check_database_size(db_session, trainers, date.today(), size_mb=10_000) == 0
    monkeypatch.setattr(settings, "DATABASE_SIZE_LIMIT_MB", 500)
    assert check_database_size(db_session, trainers, date.today()) == 0  # SQLite: not measurable
