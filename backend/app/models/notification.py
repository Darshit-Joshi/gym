import enum
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class NotificationType(str, enum.Enum):
    ABSENCE_STREAK = "ABSENCE_STREAK"
    ABSENCE_MONTHLY = "ABSENCE_MONTHLY"
    FEE_DUE_SOON = "FEE_DUE_SOON"
    FEE_OVERDUE = "FEE_OVERDUE"
    STORAGE_LOW = "STORAGE_LOW"


class NotificationSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class EmailStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class Notification(Base):
    """An alert delivered to one user (the trainer or a client).

    `dedupe_key` makes alert generation idempotent: the scheduler can run as often as it
    likes and each condition (e.g. one absence streak, one overdue fee) alerts exactly once.
    """

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id", ondelete="CASCADE"), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    fee_id = Column(Integer, ForeignKey("fee_records.id", ondelete="CASCADE"), nullable=True)
    type = Column(String(30), nullable=False, index=True)
    severity = Column(String(10), nullable=False, default=NotificationSeverity.INFO.value)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    # Ready-to-send text the trainer can forward to the client (WhatsApp/SMS)
    client_message = Column(Text, nullable=True)
    dedupe_key = Column(String(150), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False, server_default="false", index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    email_status = Column(String(10), nullable=True, index=True)
    email_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User")
    client = relationship("Client")

    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_notification_user_dedupe"),)
