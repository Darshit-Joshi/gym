from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, func

from app.core.database import Base


class StoredFile(Base):
    """Photo bytes kept in the database (STORAGE_BACKEND=database).

    Used on hosts without a persistent disk (Render free) so photos need no extra service.
    `key` is the same storage key that clients.profile_photo / progress_photos.photo_path hold.
    """

    __tablename__ = "stored_files"

    key = Column(String(100), primary_key=True)
    content_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
