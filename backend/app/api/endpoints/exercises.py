from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_current_trainer
from app.models.user import User
from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseCreate, ExerciseUpdate, ExerciseResponse

router = APIRouter()


@router.get("", response_model=List[ExerciseResponse])
def get_exercises(
    muscle_group: Optional[str] = Query(None, description="Filter by muscle group"),
    equipment: Optional[str] = Query(None, description="Filter by equipment"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    search: Optional[str] = Query(None, description="Search exercise by name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Exercise)
    if muscle_group and muscle_group.lower() != "all":
        query = query.filter(Exercise.muscle_group.ilike(muscle_group))
    if equipment and equipment.lower() != "all":
        query = query.filter(Exercise.equipment.ilike(equipment))
    if difficulty and difficulty.lower() != "all":
        query = query.filter(Exercise.difficulty.ilike(difficulty))
    if search:
        query = query.filter(Exercise.name.ilike(f"%{search.strip()}%"))

    exercises = query.order_by(Exercise.muscle_group.asc(), Exercise.name.asc()).all()
    return exercises


@router.post("", response_model=ExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(
    exercise_in: ExerciseCreate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    name_clean = exercise_in.name.strip()
    existing = db.query(Exercise).filter(Exercise.name.ilike(name_clean)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An exercise named '{name_clean}' already exists",
        )

    exercise = Exercise(
        name=name_clean,
        muscle_group=exercise_in.muscle_group.strip(),
        equipment=exercise_in.equipment.strip() if exercise_in.equipment else None,
        difficulty=exercise_in.difficulty.strip() if exercise_in.difficulty else None,
        description=exercise_in.description.strip() if exercise_in.description else None,
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with id {exercise_id} not found",
        )
    return exercise


@router.put("/{exercise_id}", response_model=ExerciseResponse)
def update_exercise(
    exercise_id: int,
    exercise_in: ExerciseUpdate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with id {exercise_id} not found",
        )

    if exercise_in.name:
        name_clean = exercise_in.name.strip()
        existing = (
            db.query(Exercise)
            .filter(Exercise.name.ilike(name_clean), Exercise.id != exercise_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another exercise named '{name_clean}' already exists",
            )
        exercise.name = name_clean

    if exercise_in.muscle_group:
        exercise.muscle_group = exercise_in.muscle_group.strip()
    if exercise_in.equipment is not None:
        exercise.equipment = exercise_in.equipment.strip() if exercise_in.equipment else None
    if exercise_in.difficulty is not None:
        exercise.difficulty = exercise_in.difficulty.strip() if exercise_in.difficulty else None
    if exercise_in.description is not None:
        exercise.description = exercise_in.description.strip() if exercise_in.description else None

    db.commit()
    db.refresh(exercise)
    return exercise


@router.delete("/{exercise_id}")
def delete_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exercise with id {exercise_id} not found",
        )

    # Check if used in workout exercises
    if exercise.workout_exercises or exercise.session_exercises:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete this exercise because it is used in workout plans or recorded sessions",
        )

    db.delete(exercise)
    db.commit()
    return {"message": "Exercise deleted successfully"}
