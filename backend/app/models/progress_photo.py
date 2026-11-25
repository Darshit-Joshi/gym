import enum
from sqlalchemy import Column, Integer, Float, String, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class PhotoCategory(str, enum.Enum):
    FRONT = "FRONT"
    SIDE = "SIDE"
    BACK = "BACK"
    OTHER = "OTHER"


class ProgressPhoto(Base):
    __tablename__ = "progress_photos"

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
    photo_date = Column(Date, nullable=False, index=True)
    photo_path = Column(String(500), nullable=False)  # storage key, e.g. progress/{uuid}.jpg
    category = Column(String(50), nullable=False, default=PhotoCategory.FRONT.value)
    weight = Column(Float, nullable=True)  # kg on the day the photo was taken (optional)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    client = relationship("Client", back_populates="progress_photos")
    trainer = relationship("Trainer")
