from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import settings as app_settings
from app.models.trainer_settings import TrainerSettings


def get_or_create_settings(db: Session, trainer_id: int) -> TrainerSettings:
    row = db.query(TrainerSettings).filter(TrainerSettings.trainer_id == trainer_id).first()
    if row:
        return row
    row = TrainerSettings(trainer_id=trainer_id, currency=app_settings.DEFAULT_CURRENCY[:3].upper())
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Another request created it concurrently
        db.rollback()
        return db.query(TrainerSettings).filter(TrainerSettings.trainer_id == trainer_id).one()
    db.refresh(row)
    return row
