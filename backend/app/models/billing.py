import enum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    OTHER = "OTHER"


class FeeStatus(str, enum.Enum):
    """Derived status of a fee record. Never stored: computed from amounts and dates."""
    PAID = "PAID"
    WAIVED = "WAIVED"
    OVERDUE = "OVERDUE"
    PARTIAL = "PARTIAL"
    PENDING = "PENDING"
    UPCOMING = "UPCOMING"


class MembershipPlan(Base):
    """A fee plan the trainer offers, e.g. 'Monthly - 1500' or 'Quarterly - 4000'."""

    __tablename__ = "membership_plans"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    duration_months = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    trainer = relationship("Trainer")
    clients = relationship("Client", back_populates="membership_plan")

    __table_args__ = (
        UniqueConstraint("trainer_id", "name", name="uq_membership_plan_trainer_name"),
        CheckConstraint("price > 0", name="ck_membership_plan_price_positive"),
        CheckConstraint("duration_months BETWEEN 1 AND 24", name="ck_membership_plan_duration"),
    )


class FeeRecord(Base):
    """One billing period's dues for one client."""

    __tablename__ = "fee_records"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("membership_plans.id", ondelete="SET NULL"), nullable=True)
    plan_name = Column(String(100), nullable=True)  # snapshot so history survives plan edits
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    amount_due = Column(Numeric(10, 2), nullable=False)
    amount_paid = Column(Numeric(10, 2), nullable=False, default=0, server_default="0")
    is_waived = Column(Boolean, nullable=False, default=False, server_default="false")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    client = relationship("Client", back_populates="fee_records")
    plan = relationship("MembershipPlan")
    payments = relationship(
        "FeePayment",
        back_populates="fee",
        cascade="all, delete-orphan",
        order_by="FeePayment.paid_on.desc(), FeePayment.id.desc()",
    )

    __table_args__ = (
        UniqueConstraint("client_id", "period_start", name="uq_fee_client_period_start"),
        CheckConstraint("amount_due > 0", name="ck_fee_amount_due_positive"),
        CheckConstraint("amount_paid >= 0", name="ck_fee_amount_paid_non_negative"),
        CheckConstraint("period_end >= period_start", name="ck_fee_period_order"),
    )


class FeePayment(Base):
    __tablename__ = "fee_payments"

    id = Column(Integer, primary_key=True, index=True)
    fee_id = Column(Integer, ForeignKey("fee_records.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    paid_on = Column(Date, nullable=False, index=True)
    method = Column(String(20), nullable=False, default=PaymentMethod.CASH.value)
    reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    fee = relationship("FeeRecord", back_populates="payments")
    recorder = relationship("User")

    __table_args__ = (CheckConstraint("amount > 0", name="ck_fee_payment_amount_positive"),)
