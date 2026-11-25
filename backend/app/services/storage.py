"""Photo storage.

Images are validated, re-encoded (which strips EXIF) and resized here, then kept either on
local disk (STORAGE_BACKEND=local, the Docker/VPS default) or in an S3-compatible bucket such
as Cloudflare R2 or AWS S3 (STORAGE_BACKEND=s3, for hosts like Render whose disk is wiped on
every deploy). Buckets stay private: the API streams images to signed-in users only.
"""
import io
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, status

try:
    from PIL import Image, ImageOps
    HAS_PILLOW = True
except ImportError:
    Image = None
    ImageOps = None
    HAS_PILLOW = False

from app.core.config import settings

ALLOWED_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}

ALLOWED_MIME_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}

MEDIA_TYPES_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

# Keys this module generates: "<subfolder>/<32 hex chars>.<ext>". Anything else is refused,
# which also rules out path traversal for both backends.
_STORAGE_KEY_RE = re.compile(r"^(profiles|progress)/[0-9a-f]{32}\.(jpg|jpeg|png|webp)$")


def _use_s3() -> bool:
    return settings.STORAGE_BACKEND == "s3"


@lru_cache(maxsize=1)
def _s3_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        region_name=settings.S3_REGION or "auto",
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def _is_missing_object_error(exc: Exception) -> bool:
    response = getattr(exc, "response", None) or {}
    code = str(response.get("Error", {}).get("Code", ""))
    return code in ("NoSuchKey", "404", "NotFound")


def get_upload_dir() -> Path:
    upload_path = Path(settings.UPLOAD_DIR).resolve()
    upload_path.mkdir(parents=True, exist_ok=True)
    (upload_path / "profiles").mkdir(parents=True, exist_ok=True)
    (upload_path / "progress").mkdir(parents=True, exist_ok=True)
    return upload_path


def media_type_for(storage_key: str) -> str:
    return MEDIA_TYPES_BY_EXTENSION.get(Path(storage_key).suffix.lower(), "image/jpeg")


def _encode_image(file_bytes: bytes, subfolder: str) -> Tuple[bytes, str]:
    """Validate the upload and return (bytes to store, Pillow format name)."""
    if HAS_PILLOW and Image:
        try:
            image = Image.open(io.BytesIO(file_bytes))
            image_format = image.format
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file or corrupted image data.",
            )

        if image_format not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format: {image_format}. Allowed formats: JPEG, PNG, WebP.",
            )

        # 1. Correct mobile photo rotation using EXIF orientation if available
        try:
            if ImageOps:
                image = ImageOps.exif_transpose(image)
        except Exception:
            pass

        # 2. Resize to optimal dimension (800x800 for profile avatars, 1600x1600 for progress photos)
        max_box = (800, 800) if subfolder == "profiles" else (1600, 1600)
        resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
        image.thumbnail(max_box, resampling)

        # 3. Re-encode (drops EXIF) with fast, optimized compression
        out = io.BytesIO()
        try:
            save_img = image
            if image_format == "JPEG":
                if save_img.mode in ("RGBA", "P"):
                    save_img = save_img.convert("RGB")
                save_img.save(out, format="JPEG", quality=85, optimize=True)
            elif image_format == "PNG":
                save_img.save(out, format="PNG", optimize=True)
            elif image_format == "WEBP":
                save_img.save(out, format="WEBP", quality=85)
            else:
                save_img.save(out, format=image_format)
        except Exception:
            out = io.BytesIO()
            image.save(out, format=image_format)
        return out.getvalue(), image_format

    # Fallback without Pillow: validate magic bytes directly
    if file_bytes.startswith(b"\xff\xd8\xff"):
        image_format = "JPEG"
    elif file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        image_format = "PNG"
    elif file_bytes.startswith(b"RIFF") and len(file_bytes) > 12 and file_bytes[8:12] == b"WEBP":
        image_format = "WEBP"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file or unsupported image format. Allowed formats: JPEG, PNG, WebP.",
        )
    return file_bytes, image_format


def validate_and_save_image(
    file_bytes: bytes,
    subfolder: str = "profiles",
) -> Tuple[str, str]:
    """
    Validates uploaded image bytes:
    1. Enforces upload size limit.
    2. Validates real image contents via Pillow.
    3. Strips EXIF metadata for privacy.
    4. Generates a secure, unique key to prevent collisions & traversal.
    5. Stores it on disk or in the bucket and returns (storage_key, content_type).
    """
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )
    if subfolder not in ("profiles", "progress"):
        raise ValueError(f"Unknown photo folder: {subfolder}")

    data, image_format = _encode_image(file_bytes, subfolder)
    storage_key = f"{subfolder}/{uuid.uuid4().hex}{ALLOWED_EXTENSIONS[image_format]}"
    content_type = f"image/{image_format.lower()}"

    if _use_s3():
        try:
            _s3_client().put_object(
                Bucket=settings.S3_BUCKET,
                Key=storage_key,
                Body=data,
                ContentType=content_type,
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Photo storage is unavailable right now. Please try again.",
            )
    else:
        target_path = get_upload_dir() / storage_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)

    return storage_key, content_type


def _check_key(storage_key: str) -> None:
    if not storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No image found.")
    if not _STORAGE_KEY_RE.match(storage_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid file path traversal detected.",
        )


def get_secure_file_path(storage_key: str) -> Path:
    """
    Local backend only: resolves storage key to an absolute Path inside the upload directory.
    """
    _check_key(storage_key)
    base_dir = get_upload_dir()
    resolved_path = (base_dir / storage_key).resolve()
    try:
        resolved_path.relative_to(base_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid file path traversal detected.",
        )

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested file does not exist on server.",
        )

    return resolved_path


def read_image(storage_key: str) -> Tuple[bytes, str]:
    """Return (image bytes, media type) for a stored photo, from disk or the bucket."""
    _check_key(storage_key)
    if not _use_s3():
        return get_secure_file_path(storage_key).read_bytes(), media_type_for(storage_key)

    try:
        obj = _s3_client().get_object(Bucket=settings.S3_BUCKET, Key=storage_key)
        return obj["Body"].read(), media_type_for(storage_key)
    except Exception as exc:
        if _is_missing_object_error(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested file does not exist on server.",
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo storage is unavailable right now. Please try again.",
        )


def delete_secure_file(storage_key: str) -> bool:
    """
    Deletes the stored photo for storage_key. Never raises: a leftover file is harmless,
    a failed request because of one is not.
    """
    if not storage_key:
        return False

    try:
        if _use_s3():
            _check_key(storage_key)
            _s3_client().delete_object(Bucket=settings.S3_BUCKET, Key=storage_key)
            return True
        file_path = get_secure_file_path(storage_key)
        if file_path.exists():
            file_path.unlink()
            return True
    except Exception:
        pass
    return False
