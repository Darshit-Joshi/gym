from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(
        Integer,
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    trainer_id = Column(
        Integer,
        ForeignKey("trainers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    client = relationship("Client", back_populates="workout_plans")
    trainer = relationship("Trainer", back_populates="workout_plans")
    days = relationship(
        "WorkoutDay",
        back_populates="workout_plan",
        cascade="all, delete-orphan",
        order_by="WorkoutDay.day_order",
    )
    sessions = relationship("WorkoutSession", back_populates="workout_plan")


class WorkoutDay(Base):
    __tablename__ = "workout_days"

    id = Column(Integer, primary_key=True, index=True)
    workout_plan_id = Column(
        Integer,
        ForeignKey("workout_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_name = Column(String(100), nullable=False)  # e.g., "Monday - Chest & Triceps"
    day_order = Column(Integer, default=1, nullable=False)
    is_rest_day = Column(Boolean, default=False, nullable=False)

    workout_plan = relationship("WorkoutPlan", back_populates="days")
    exercises = relationship(
        "WorkoutExercise",
        back_populates="workout_day",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, index=True)
    workout_day_id = Column(
        Integer,
        ForeignKey("workout_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id = Column(
        Integer,
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sets = Column(Integer, default=3, nullable=False)
    reps = Column(Integer, default=10, nullable=False)
    weight = Column(Float, nullable=True)  # target weight in kg
    rest_seconds = Column(Integer, default=60, nullable=False)
    instructions = Column(Text, nullable=True)
    order_index = Column(Integer, default=1, nullable=False)

    workout_day = relationship("WorkoutDay", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="workout_exercises")
