from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ExerciseBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    muscle_group: str = Field(..., min_length=2, max_length=100)
    equipment: Optional[str] = None
    difficulty: Optional[str] = None
    description: Optional[str] = None


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    muscle_group: Optional[str] = Field(None, min_length=2, max_length=100)
    equipment: Optional[str] = None
    difficulty: Optional[str] = None
    description: Optional[str] = None


class ExerciseResponse(ExerciseBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
