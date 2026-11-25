from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TrainerNoteCreate(BaseModel):
    note: str = Field(..., min_length=1)


class TrainerNoteUpdate(BaseModel):
    note: str = Field(..., min_length=1)


class TrainerNoteResponse(BaseModel):
    id: int
    client_id: int
    trainer_id: int
    trainer_name: Optional[str] = None
    note: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
