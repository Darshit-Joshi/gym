from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class TrainerSettings(Base):
    """Per-trainer billing and alert preferences. Created lazily with defaults."""

    __tablename__ = "trainer_settings"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False, unique=True)
    currency = Column(String(3), nullable=False, default="INR", server_default="INR")
    # Days after the due date before an unpaid fee counts as overdue
    fee_grace_days = Column(Integer, nullable=False, default=5, server_default="5")
    # Days before the due date at which clients get a "fee due soon" reminder
    fee_reminder_days = Column(Integer, nullable=False, default=3, server_default="3")
    # Consecutive recorded absences that trigger an alert
    absence_streak_threshold = Column(Integer, nullable=False, default=3, server_default="3")
    # Absences within one calendar month that trigger an alert
    absence_monthly_threshold = Column(Integer, nullable=False, default=6, server_default="6")
    email_clients = Column(Boolean, nullable=False, default=False, server_default="false")
    email_trainer = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    trainer = relationship("Trainer")
