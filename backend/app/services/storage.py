import io
import uuid
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


def get_upload_dir() -> Path:
    upload_path = Path(settings.UPLOAD_DIR).resolve()
    upload_path.mkdir(parents=True, exist_ok=True)
    (upload_path / "profiles").mkdir(parents=True, exist_ok=True)
    (upload_path / "progress").mkdir(parents=True, exist_ok=True)
    return upload_path


def validate_and_save_image(
    file_bytes: bytes,
    subfolder: str = "profiles",
) -> Tuple[str, str]:
    """
    Validates uploaded image bytes:
    1. Enforces upload size limit.
    2. Validates real image contents via Pillow.
    3. Strips EXIF metadata for privacy.
    4. Generates a secure, unique filename to prevent collisions & traversal.
    5. Returns (storage_key, content_type).
    """
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

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

        ext = ALLOWED_EXTENSIONS[image_format]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        base_dir = get_upload_dir()
        sub_dir = base_dir / subfolder
        sub_dir.mkdir(parents=True, exist_ok=True)
        target_path = sub_dir / unique_filename

        # 3. Strip EXIF and save with fast, optimized compression
        try:
            save_img = image
            if image_format == "JPEG":
                if save_img.mode in ("RGBA", "P"):
                    save_img = save_img.convert("RGB")
                save_img.save(target_path, format="JPEG", quality=85, optimize=True)
            elif image_format == "PNG":
                save_img.save(target_path, format="PNG", optimize=True)
            elif image_format == "WEBP":
                save_img.save(target_path, format="WEBP", quality=85)
            else:
                save_img.save(target_path, format=image_format)
        except Exception:
            # Fallback to direct save
            image.save(target_path, format=image_format)
    else:
        # Fallback: Validate magic bytes directly
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

        ext = ALLOWED_EXTENSIONS[image_format]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        base_dir = get_upload_dir()
        sub_dir = base_dir / subfolder
        sub_dir.mkdir(parents=True, exist_ok=True)
        target_path = sub_dir / unique_filename
        target_path.write_bytes(file_bytes)

    storage_key = f"{subfolder}/{unique_filename}"
    content_type = f"image/{image_format.lower()}"
    return storage_key, content_type


def get_secure_file_path(storage_key: str) -> Path:
    """
    Resolves storage key to absolute Path and verifies it stays within upload directory
    to prevent path traversal attacks.
    """
    if not storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No image found.",
        )

    base_dir = get_upload_dir()
    # Normalize path and prevent directory traversal
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


def delete_secure_file(storage_key: str) -> bool:
    """
    Deletes the file corresponding to storage_key safely.
    """
    if not storage_key:
        return False

    try:
        file_path = get_secure_file_path(storage_key)
        if file_path.exists():
            file_path.unlink()
            return True
    except Exception:
        pass
    return False
