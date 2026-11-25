from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Trainer(Base):
    __tablename__ = "trainers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    profile_image = Column(String(500), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="trainer_profile")
    clients = relationship("Client", back_populates="trainer")
    workout_plans = relationship("WorkoutPlan", back_populates="trainer")
    sessions = relationship("WorkoutSession", back_populates="trainer")
    notes = relationship("TrainerNote", back_populates="trainer")
