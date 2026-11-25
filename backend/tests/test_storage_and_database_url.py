"""Photo storage on an S3-compatible bucket (R2/S3) and hosted-Postgres connection strings (Neon)."""
import io
import ssl

import boto3
import pytest
from fastapi import HTTPException
from moto import mock_aws
from PIL import Image

from app.core.config import settings, validate_production_settings
from app.core.database import engine_options
from app.services import storage

BUCKET = "gym-photos-test"


def _png(size=(40, 60)):
    buf = io.BytesIO()
    Image.new("RGB", size, color=(200, 40, 40)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def s3_bucket(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET", BUCKET)
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "")
    monkeypatch.setattr(settings, "S3_REGION", "us-east-1")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY_ID", "test")
    monkeypatch.setattr(settings, "S3_SECRET_ACCESS_KEY", "test")
    storage._s3_client.cache_clear()
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        yield s3
    storage._s3_client.cache_clear()


# ---------------------------------------------------------------- S3 storage

def test_s3_save_read_delete_roundtrip(s3_bucket):
    key, content_type = storage.validate_and_save_image(_png(), subfolder="progress")
    assert key.startswith("progress/") and key.endswith(".png")
    assert content_type == "image/png"

    stored = s3_bucket.get_object(Bucket=BUCKET, Key=key)
    assert stored["ContentType"] == "image/png"

    data, media_type = storage.read_image(key)
    assert media_type == "image/png"
    assert Image.open(io.BytesIO(data)).size == (40, 60)

    assert storage.delete_secure_file(key) is True
    with pytest.raises(HTTPException) as exc:
        storage.read_image(key)
    assert exc.value.status_code == 404


def test_s3_resizes_and_strips_before_upload(s3_bucket):
    key, _ = storage.validate_and_save_image(_png((3000, 2000)), subfolder="profiles")
    data, _ = storage.read_image(key)
    assert max(Image.open(io.BytesIO(data)).size) == 800


def test_s3_rejects_keys_it_did_not_generate(s3_bucket):
    for bad in ("../etc/passwd", "profiles/../../secret.png", "other/abc.png", "profiles/x.png"):
        with pytest.raises(HTTPException) as exc:
            storage.read_image(bad)
        assert exc.value.status_code == 403
    assert storage.delete_secure_file("../etc/passwd") is False


def test_s3_outage_is_a_clean_503(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")

    class Broken:
        def put_object(self, **kw):
            raise ConnectionError("bucket unreachable")

        def get_object(self, **kw):
            raise ConnectionError("bucket unreachable")

    monkeypatch.setattr(storage, "_s3_client", lambda: Broken())
    with pytest.raises(HTTPException) as exc:
        storage.validate_and_save_image(_png(), subfolder="profiles")
    assert exc.value.status_code == 503
    with pytest.raises(HTTPException) as exc:
        storage.read_image("profiles/" + "a" * 32 + ".png")
    assert exc.value.status_code == 503


def test_client_photo_api_with_s3(client, s3_bucket):
    reg = client.post(
        "/api/auth/register-trainer",
        json={"name": "Bucket Trainer", "email": "bucket.trainer@testgym.com", "password": "Password123!"},
    )
    login = client.post(
        "/api/auth/login", json={"email": "bucket.trainer@testgym.com", "password": "Password123!"}
    )
    assert login.status_code == 200, (reg.text, login.text)
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    c = client.post("/api/clients", json={"name": "Bucket Client"}, headers=headers).json()
    up = client.post(
        f"/api/clients/{c['id']}/photo",
        files={"file": ("me.png", _png(), "image/png")},
        headers=headers,
    )
    assert up.status_code == 200, up.text
    key = up.json()["profile_photo"]
    assert s3_bucket.head_object(Bucket=BUCKET, Key=key)

    img = client.get(f"/api/clients/{c['id']}/photo", headers=headers)
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"
    assert img.headers["cache-control"].startswith("private")

    # Replacing the photo removes the old object from the bucket
    up2 = client.post(
        f"/api/clients/{c['id']}/photo",
        files={"file": ("me2.png", _png(), "image/png")},
        headers=headers,
    )
    assert up2.status_code == 200
    keys = [o["Key"] for o in s3_bucket.list_objects_v2(Bucket=BUCKET).get("Contents", [])]
    assert key not in keys and up2.json()["profile_photo"] in keys

    assert client.get(f"/api/clients/{c['id']}/photo").status_code == 401


def test_production_requires_bucket_settings(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "x" * 64)
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql+pg8000://u:p@h/db")
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET", "")
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        validate_production_settings(settings)


# ---------------------------------------------------------------- database URLs

def test_neon_connection_string_is_accepted_as_is():
    url, connect_args = engine_options(
        "postgresql://neondb_owner:pa%25ss@ep-cool-name-123.us-east-2.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    assert url.drivername == "postgresql+pg8000"
    assert url.host == "ep-cool-name-123.us-east-2.aws.neon.tech"
    assert url.password == "pa%ss"
    assert dict(url.query) == {}
    ctx = connect_args["ssl_context"]
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname


def test_postgres_scheme_alias_and_plain_local_url():
    url, connect_args = engine_options("postgres://u:p@localhost:5433/gym_db")
    assert url.drivername == "postgresql+pg8000" and connect_args == {}

    url, connect_args = engine_options("postgresql+pg8000://postgres:pw@localhost:5433/gym_db")
    assert url.drivername == "postgresql+pg8000" and connect_args == {}


def test_sqlite_url_keeps_thread_flag():
    _, connect_args = engine_options("sqlite:///:memory:")
    assert connect_args == {"check_same_thread": False}
