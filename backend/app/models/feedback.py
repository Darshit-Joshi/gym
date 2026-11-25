import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class FeedbackCategory(str, enum.Enum):
    WORKOUT_DIFFICULTY = "Workout Difficulty"
    ENERGY_LEVELS = "Energy Levels"
    RECOVERY = "Recovery"
    EXERCISE_PREFERENCE = "Exercise Preference"
    SATISFACTION = "Satisfaction"
    GENERAL = "General Feedback"


class FollowUpStatus(str, enum.Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"


class ClientFeedback(Base):
    __tablename__ = "client_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(
        Integer,
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trainer_id = Column(
        Integer,
        ForeignKey("trainers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(Date, nullable=False, index=True)
    category = Column(String(50), nullable=False, default=FeedbackCategory.GENERAL.value)
    feedback_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)  # 1 to 5 scale
    follow_up_required = Column(Boolean, nullable=False, default=False)
    follow_up_status = Column(String(50), nullable=False, default=FollowUpStatus.NONE.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    client = relationship("Client", back_populates="feedbacks")
    trainer = relationship("Trainer")
