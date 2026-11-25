from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload, selectinload
from app.core.timezone import today_gym
from app.api.deps import (
    get_db,
    get_current_user,
    get_current_trainer,
    verify_client_access,
)
from app.models.user import User, UserRole
from app.models.trainer import Trainer
from app.models.client import Client
from app.models.session import WorkoutSession, WorkoutSessionExercise
from app.models.exercise import Exercise
from app.schemas.session import (
    DayExercisesSet,
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionExerciseResponse,
)

router = APIRouter()


def _format_session_response(sess: WorkoutSession, db: Session) -> SessionResponse:
    exercises_resp = []
    for se in sess.session_exercises:
        ex = se.exercise
        exercises_resp.append(
            SessionExerciseResponse(
                id=se.id,
                exercise_id=se.exercise_id,
                exercise_name=ex.name if ex else "Unknown",
                muscle_group=ex.muscle_group if ex else "Other",
                sets_completed=se.sets_completed,
                reps=se.reps,
                weight_used=se.weight_used,
                notes=se.notes,
            )
        )

    return SessionResponse(
        id=sess.id,
        client_id=sess.client_id,
        client_name=sess.client.name if sess.client else None,
        trainer_id=sess.trainer_id,
        workout_plan_id=sess.workout_plan_id,
        workout_name=sess.workout_name,
        date=sess.date,
        duration_minutes=sess.duration_minutes,
        notes=sess.notes,
        status=sess.status,
        exercises=exercises_resp,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
    )


@router.get("", response_model=List[SessionResponse])
def get_sessions(
    client_id: Optional[int] = Query(None, description="Filter by client id"),
    session_date: Optional[date] = Query(None, description="Filter by session date"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Return only the most recent N days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(WorkoutSession)

    trainer = db.query(Trainer).filter(Trainer.user_id == current_user.id).first()
    if not trainer:
        return []
    query = query.filter(WorkoutSession.trainer_id == trainer.id)
    if client_id:
        client = db.query(Client).filter(Client.id == client_id, Client.trainer_id == trainer.id).first()
        if not client:
            return []
        query = query.filter(WorkoutSession.client_id == client.id)

    if session_date:
        query = query.filter(WorkoutSession.date == session_date)

    query = query.options(
        selectinload(WorkoutSession.session_exercises).joinedload(WorkoutSessionExercise.exercise),
        joinedload(WorkoutSession.client),
    ).order_by(WorkoutSession.date.desc(), WorkoutSession.id.desc())
    if limit:
        query = query.limit(limit)
    return [_format_session_response(s, db) for s in query.all()]


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def record_session(
    session_in: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify client access
    client = verify_client_access(session_in.client_id, current_user, db)

    trainer_id = client.trainer_id
    if current_user.role == UserRole.TRAINER.value:
        trainer_id = current_user.trainer_profile.id if current_user.trainer_profile else client.trainer_id

    # Prevent rapid duplicate submissions (accidental double submit within 10 seconds)
    recent_sess = (
        db.query(WorkoutSession)
        .filter(
            WorkoutSession.client_id == client.id,
            WorkoutSession.date == session_in.date,
            WorkoutSession.workout_name == (session_in.workout_name or "Daily Workout Session"),
        )
        .order_by(WorkoutSession.id.desc())
        .first()
    )
    if recent_sess and recent_sess.created_at:
        sess_created = recent_sess.created_at
        if sess_created.tzinfo is None:
            sess_created = sess_created.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (now - sess_created).total_seconds()
        if 0 <= delta <= 10:
            return _format_session_response(recent_sess, db)

    sess = WorkoutSession(
        client_id=client.id,
        trainer_id=trainer_id,
        workout_plan_id=session_in.workout_plan_id,
        workout_name=session_in.workout_name or "Daily Workout Session",
        date=session_in.date,
        duration_minutes=session_in.duration_minutes,
        notes=session_in.notes,
        status=session_in.status or "COMPLETED",
    )
    db.add(sess)
    db.flush()

    for ex_in in session_in.exercises:
        exercise = db.query(Exercise).filter(Exercise.id == ex_in.exercise_id).first()
        if not exercise:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exercise with id {ex_in.exercise_id} not found",
            )
        se = WorkoutSessionExercise(
            session_id=sess.id,
            exercise_id=exercise.id,
            sets_completed=ex_in.sets_completed,
            reps=ex_in.reps,
            weight_used=ex_in.weight_used,
            notes=ex_in.notes,
        )
        db.add(se)

    db.commit()
    db.refresh(sess)
    return _format_session_response(sess, db)


def _workout_name_for(exercises: List[Exercise]) -> str:
    """Name a day after its muscle groups, e.g. "Chest + Triceps"."""
    groups: List[str] = []
    for ex in exercises:
        if ex.muscle_group and ex.muscle_group not in groups:
            groups.append(ex.muscle_group)
    if not groups:
        return "Daily Workout Session"
    if len(groups) > 3:
        return " + ".join(groups[:3]) + " + more"
    return " + ".join(groups)


@router.put("/day", response_model=Optional[SessionResponse])
def set_day_exercises(
    day_in: DayExercisesSet,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    """Store the exercises a client did on a day.

    There is one record per client per day: saving again replaces that day's
    list. Exercises kept from before keep any sets/reps already stored.
    Saving an empty list removes the day's record and returns null.
    """
    current_user, trainer = trainer_data
    client = verify_client_access(day_in.client_id, current_user, db)
    if day_in.date > today_gym():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workouts cannot be logged for a future date",
        )

    # Keep the order the trainer picked, without duplicates.
    exercise_ids = list(dict.fromkeys(day_in.exercise_ids))
    exercises = db.query(Exercise).filter(Exercise.id.in_(exercise_ids)).all() if exercise_ids else []
    by_id = {ex.id: ex for ex in exercises}
    missing = [eid for eid in exercise_ids if eid not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exercise with id {missing[0]} not found",
        )
    ordered = [by_id[eid] for eid in exercise_ids]

    day_sessions = (
        db.query(WorkoutSession)
        .filter(
            WorkoutSession.client_id == client.id,
            WorkoutSession.trainer_id == trainer.id,
            WorkoutSession.date == day_in.date,
        )
        .order_by(WorkoutSession.id.asc())
        .all()
    )
    sess = day_sessions[0] if day_sessions else None

    if not ordered:
        if sess:
            db.delete(sess)
            db.commit()
        return None

    if sess is None:
        sess = WorkoutSession(
            client_id=client.id,
            trainer_id=trainer.id,
            date=day_in.date,
            status="COMPLETED",
        )
        db.add(sess)
        db.flush()

    sess.workout_name = _workout_name_for(ordered)
    if day_in.notes is not None:
        sess.notes = day_in.notes.strip() or None

    existing = {se.exercise_id: se for se in sess.session_exercises}
    wanted = set(exercise_ids)
    for se in list(sess.session_exercises):
        if se.exercise_id not in wanted:
            sess.session_exercises.remove(se)
    for ex in ordered:
        if ex.id not in existing:
            existing[ex.id] = WorkoutSessionExercise(exercise_id=ex.id)
            sess.session_exercises.append(existing[ex.id])
    for detail in day_in.details or []:
        se = existing.get(detail.exercise_id)
        if se is None or detail.exercise_id not in wanted:
            continue
        se.sets_completed = detail.sets_completed
        se.reps = detail.reps
        se.weight_used = detail.weight_used

    db.commit()
    db.refresh(sess)
    return _format_session_response(sess, db)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sess = db.query(WorkoutSession).filter(WorkoutSession.id == session_id).first()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found",
        )

    verify_client_access(sess.client_id, current_user, db)
    if current_user.role == UserRole.TRAINER.value:
        trainer = db.query(Trainer).filter(Trainer.user_id == current_user.id).first()
        if not trainer or sess.trainer_id != trainer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot access another trainer's workout session",
            )
    return _format_session_response(sess, db)


@router.put("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: int,
    session_in: SessionUpdate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    sess = db.query(WorkoutSession).filter(WorkoutSession.id == session_id, WorkoutSession.trainer_id == trainer.id).first()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found",
        )

    if session_in.date:
        sess.date = session_in.date
    if session_in.workout_name:
        sess.workout_name = session_in.workout_name
    if session_in.duration_minutes is not None:
        sess.duration_minutes = session_in.duration_minutes
    if session_in.notes is not None:
        sess.notes = session_in.notes
    if session_in.status:
        sess.status = session_in.status

    if session_in.exercises is not None:
        # Replace exercises
        db.query(WorkoutSessionExercise).filter(
            WorkoutSessionExercise.session_id == sess.id
        ).delete()
        for ex_in in session_in.exercises:
            se = WorkoutSessionExercise(
                session_id=sess.id,
                exercise_id=ex_in.exercise_id,
                sets_completed=ex_in.sets_completed,
                reps=ex_in.reps,
                weight_used=ex_in.weight_used,
                notes=ex_in.notes,
            )
            db.add(se)

    db.commit()
    db.refresh(sess)
    return _format_session_response(sess, db)


@router.post("/{session_id}/complete")
def complete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sess = db.query(WorkoutSession).filter(WorkoutSession.id == session_id).first()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found",
        )

    verify_client_access(sess.client_id, current_user, db)
    if current_user.role == UserRole.TRAINER.value:
        trainer = db.query(Trainer).filter(Trainer.user_id == current_user.id).first()
        if not trainer or sess.trainer_id != trainer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot access another trainer's workout session",
            )
    sess.status = "COMPLETED"
    db.commit()
    return {"message": "Session marked as completed", "status": "COMPLETED"}


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    sess = db.query(WorkoutSession).filter(WorkoutSession.id == session_id, WorkoutSession.trainer_id == trainer.id).first()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found",
        )
    db.delete(sess)
    db.commit()
    return {"message": "Session deleted successfully"}
