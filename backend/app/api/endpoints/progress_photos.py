"""Weekly progress photos for a client, so the trainer can see changes over time."""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_trainer,
    get_current_user_with_media_token,
    get_db,
    verify_client_access,
)
from app.core.timezone import today_gym
from app.models.client import ClientStatus
from app.models.progress_photo import ProgressPhoto
from app.models.trainer import Trainer
from app.models.user import User
from app.schemas.progress_photo import (
    PHOTO_CATEGORIES,
    ProgressPhotoResponse,
    ProgressPhotoUpdate,
)
from app.services.storage import delete_secure_file, read_image, validate_and_save_image

router = APIRouter()


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _response(photo: ProgressPhoto) -> ProgressPhotoResponse:
    return ProgressPhotoResponse(
        id=photo.id,
        client_id=photo.client_id,
        photo_date=photo.photo_date,
        week_start=_week_start(photo.photo_date),
        category=photo.category,
        weight=photo.weight,
        notes=photo.notes,
        image_url=f"/api/progress-photos/{photo.id}/image",
        created_at=photo.created_at,
    )


def _get_photo(db: Session, photo_id: int, trainer_id: int) -> ProgressPhoto:
    photo = (
        db.query(ProgressPhoto)
        .filter(ProgressPhoto.id == photo_id, ProgressPhoto.trainer_id == trainer_id)
        .first()
    )
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return photo


def _check_date(photo_date: date) -> None:
    if photo_date > today_gym():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Photo date cannot be in the future")


@router.get("", response_model=List[ProgressPhotoResponse])
def list_progress_photos(
    client_id: int = Query(..., description="Client whose photos to list"),
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    user, trainer = trainer_data
    client = verify_client_access(client_id, user, db)
    photos = (
        db.query(ProgressPhoto)
        .filter(ProgressPhoto.client_id == client.id, ProgressPhoto.trainer_id == trainer.id)
        .order_by(ProgressPhoto.photo_date.desc(), ProgressPhoto.id.desc())
        .all()
    )
    return [_response(p) for p in photos]


@router.post("", response_model=ProgressPhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_progress_photo(
    client_id: int = Form(...),
    photo_date: date = Form(...),
    category: str = Form("FRONT"),
    weight: Optional[float] = Form(None),
    notes: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    user, trainer = trainer_data
    client = verify_client_access(client_id, user, db)
    if client.status == ClientStatus.ARCHIVED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add photos to an archived client")

    # Validate the form fields with the same rules as edits.
    try:
        fields = ProgressPhotoUpdate(photo_date=photo_date, category=category, weight=weight, notes=notes)
    except ValidationError as exc:
        message = exc.errors()[0].get("msg", "Invalid photo details").removeprefix("Value error, ")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)
    _check_date(photo_date)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    storage_key, _ = validate_and_save_image(file_bytes, subfolder="progress")

    photo = ProgressPhoto(
        client_id=client.id,
        trainer_id=trainer.id,
        photo_date=photo_date,
        category=fields.category or "FRONT",
        weight=fields.weight,
        notes=(fields.notes or "").strip() or None,
        photo_path=storage_key,
    )
    db.add(photo)

    # A weight recorded with the newest photo becomes the client's current weight.
    if fields.weight is not None:
        latest = (
            db.query(func.max(ProgressPhoto.photo_date))
            .filter(ProgressPhoto.client_id == client.id, ProgressPhoto.weight.isnot(None))
            .scalar()
        )
        if latest is None or photo_date >= latest:
            client.current_weight = fields.weight

    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_secure_file(storage_key)
        raise
    db.refresh(photo)
    return _response(photo)


@router.get("/{photo_id}/image")
def get_progress_photo_image(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_media_token),
):
    """Streams the image. Accepts the token as a query parameter so <img> tags can load it."""
    trainer = db.query(Trainer).filter(Trainer.user_id == current_user.id).first()
    if not trainer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trainer role required")
    photo = _get_photo(db, photo_id, trainer.id)
    content, media_type = read_image(photo.photo_path)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.patch("/{photo_id}", response_model=ProgressPhotoResponse)
def update_progress_photo(
    photo_id: int,
    body: ProgressPhotoUpdate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    photo = _get_photo(db, photo_id, trainer.id)
    data = body.model_dump(exclude_unset=True)
    if "photo_date" in data and data["photo_date"] is not None:
        _check_date(data["photo_date"])
        photo.photo_date = data["photo_date"]
    if data.get("category"):
        photo.category = data["category"]
    if "weight" in data:
        photo.weight = data["weight"]
    if "notes" in data:
        photo.notes = (data["notes"] or "").strip() or None
    db.commit()
    db.refresh(photo)
    return _response(photo)


@router.delete("/{photo_id}")
def delete_progress_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    photo = _get_photo(db, photo_id, trainer.id)
    storage_key = photo.photo_path
    db.delete(photo)
    db.commit()
    delete_secure_file(storage_key)
    return {"message": "Photo deleted"}


__all__ = ["router", "PHOTO_CATEGORIES"]
