from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(
        Integer,
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trainer_id = Column(
        Integer,
        ForeignKey("trainers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workout_plan_id = Column(
        Integer,
        ForeignKey("workout_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workout_name = Column(String(255), nullable=True)  # e.g., "Chest + Triceps"
    date = Column(Date, nullable=False, index=True)
    duration_minutes = Column(Integer, default=60, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="COMPLETED", nullable=False)  # COMPLETED, SCHEDULED, MISSED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    client = relationship("Client", back_populates="sessions")
    trainer = relationship("Trainer", back_populates="sessions")
    workout_plan = relationship("WorkoutPlan", back_populates="sessions")
    session_exercises = relationship(
        "WorkoutSessionExercise",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkoutSessionExercise.id",
    )


class WorkoutSessionExercise(Base):
    __tablename__ = "workout_session_exercises"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id = Column(
        Integer,
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Optional: the trainer may just tick which exercises were done on the day.
    sets_completed = Column(Integer, nullable=True)
    reps = Column(Integer, nullable=True)
    weight_used = Column(Float, nullable=True)  # weight in kg
    notes = Column(Text, nullable=True)

    session = relationship("WorkoutSession", back_populates="session_exercises")
    exercise = relationship("Exercise", back_populates="session_exercises")
