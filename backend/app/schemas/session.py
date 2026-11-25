from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SessionExerciseBase(BaseModel):
    exercise_id: int
    sets_completed: Optional[int] = Field(None, ge=1, le=50)
    reps: Optional[int] = Field(None, ge=1, le=500)
    weight_used: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class SessionExerciseCreate(SessionExerciseBase):
    pass


class SessionExerciseResponse(SessionExerciseBase):
    id: int
    exercise_name: Optional[str] = None
    muscle_group: Optional[str] = None

    model_config = {"from_attributes": True}


class SessionBase(BaseModel):
    client_id: int
    date: date
    workout_plan_id: Optional[int] = None
    workout_name: Optional[str] = Field(None, max_length=255)
    duration_minutes: int = Field(default=60, ge=1, le=600)
    notes: Optional[str] = None
    status: str = Field(default="COMPLETED")


class SessionCreate(SessionBase):
    exercises: List[SessionExerciseCreate] = []


class DayExerciseDetail(BaseModel):
    """Optional sets/reps/weight for one exercise of the day."""

    exercise_id: int
    sets_completed: Optional[int] = Field(None, ge=1, le=50)
    reps: Optional[int] = Field(None, ge=1, le=500)
    weight_used: Optional[float] = Field(None, ge=0, le=1000)


class DayExercisesSet(BaseModel):
    """Set the exercises a client did on a given day (one record per client per day).

    `exercise_ids` is the ordered list of exercises. `details`, when sent, carries
    sets/reps/weight for some or all of them; exercises left out of `details` keep
    whatever was stored before.
    """

    client_id: int
    date: date
    exercise_ids: List[int] = Field(default_factory=list, max_length=200)
    details: Optional[List[DayExerciseDetail]] = Field(None, max_length=200)
    notes: Optional[str] = None


class SessionUpdate(BaseModel):
    date: Optional[date] = None
    workout_name: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=600)
    notes: Optional[str] = None
    status: Optional[str] = None
    exercises: Optional[List[SessionExerciseCreate]] = None


class SessionResponse(SessionBase):
    id: int
    client_name: Optional[str] = None
    trainer_id: Optional[int] = None
    exercises: List[SessionExerciseResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
