import enum
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ClientStatus(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING_ACTIVATION = "Pending Activation"
    ARCHIVED = "Archived"


class FitnessGoal(str, enum.Enum):
    MUSCLE_GAIN = "Muscle Gain"
    WEIGHT_LOSS = "Weight Loss"
    STRENGTH = "Strength"
    GENERAL_FITNESS = "General Fitness"
    ENDURANCE = "Endurance"
    OTHER = "Other"


# Clients don't sign in, but each client keeps a (login-disabled) user row because
# clients.user_id is required. Clients added without an email get a placeholder
# address on this reserved domain, which is never shown in the API.
NO_LOGIN_EMAIL_DOMAIN = "clients.no-login.invalid"


class Client(Base):
    __tablename__ = "clients"

    @property
    def email(self):
        email = self.user.email if self.user else None
        if not email or email.endswith("@" + NO_LOGIN_EMAIL_DOMAIN):
            return None
        return email

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    trainer_id = Column(
        Integer,
        ForeignKey("trainers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True, index=True)
    date_of_birth = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(50), nullable=True)
    height = Column(Float, nullable=True)  # in cm
    current_weight = Column(Float, nullable=True)  # in kg
    fitness_goal = Column(String(100), nullable=True, default=FitnessGoal.GENERAL_FITNESS.value, index=True)
    status = Column(String(50), nullable=False, default=ClientStatus.ACTIVE.value, index=True)
    profile_photo = Column(String(500), nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    joined_date = Column(Date, nullable=True)
    training_preferences = Column(Text, nullable=True)
    # Billing: a client with a plan, fee amount and start date is billed every plan cycle
    membership_plan_id = Column(
        Integer,
        ForeignKey("membership_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fee_amount = Column(Numeric(10, 2), nullable=True)
    billing_start_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="client_profile")
    trainer = relationship("Trainer", back_populates="clients")
    workout_plans = relationship("WorkoutPlan", back_populates="client", cascade="all, delete-orphan")
    sessions = relationship("WorkoutSession", back_populates="client", cascade="all, delete-orphan")
    notes = relationship("TrainerNote", back_populates="client", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="client", cascade="all, delete-orphan")
    progress_entries = relationship("ProgressEntry", back_populates="client", cascade="all, delete-orphan")
    progress_photos = relationship("ProgressPhoto", back_populates="client", cascade="all, delete-orphan")
    feedbacks = relationship("ClientFeedback", back_populates="client", cascade="all, delete-orphan")
    membership_plan = relationship("MembershipPlan", back_populates="clients")
    fee_records = relationship("FeeRecord", back_populates="client", cascade="all, delete-orphan")
