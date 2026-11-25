from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

PHOTO_CATEGORIES = ("FRONT", "SIDE", "BACK", "OTHER")


class ProgressPhotoUpdate(BaseModel):
    photo_date: Optional[date] = None
    category: Optional[str] = None
    weight: Optional[float] = Field(None, gt=0, le=500)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("category")
    @classmethod
    def _category(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().upper()
        if v not in PHOTO_CATEGORIES:
            raise ValueError(f"Pose must be one of: {', '.join(PHOTO_CATEGORIES)}")
        return v


class ProgressPhotoResponse(BaseModel):
    id: int
    client_id: int
    photo_date: date
    week_start: date  # Monday of the photo's week
    category: str
    weight: Optional[float] = None
    notes: Optional[str] = None
    image_url: str
    created_at: datetime
