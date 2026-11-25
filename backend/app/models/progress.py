from sqlalchemy import Column, Integer, Float, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProgressEntry(Base):
    __tablename__ = "progress_entries"

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
    weight = Column(Float, nullable=True)  # in kg
    height = Column(Float, nullable=True)  # in cm
    body_fat_percentage = Column(Float, nullable=True)  # %
    chest = Column(Float, nullable=True)  # in cm
    waist = Column(Float, nullable=True)  # in cm
    hips = Column(Float, nullable=True)  # in cm
    arms = Column(Float, nullable=True)  # in cm
    thighs = Column(Float, nullable=True)  # in cm
    calves = Column(Float, nullable=True)  # in cm
    shoulders = Column(Float, nullable=True)  # in cm
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    client = relationship("Client", back_populates="progress_entries")
    trainer = relationship("Trainer")
