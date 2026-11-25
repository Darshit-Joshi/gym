"""Warns the trainer before a size-capped database (e.g. Neon free, 500 MB) fills up.

Matters most with STORAGE_BACKEND=database, where photos live in the database too.
Runs with the scheduled jobs; each level (80%, 95%) alerts at most once a month.
"""
import logging
from datetime import date
from typing import Iterable, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification, NotificationSeverity, NotificationType
from app.models.trainer import Trainer

logger = logging.getLogger(__name__)

LEVELS = (
    (95, NotificationSeverity.CRITICAL),
    (80, NotificationSeverity.WARNING),
)


def database_size_mb(db: Session) -> Optional[float]:
    """Size of the current database in MB, or None where it can't be measured (SQLite)."""
    if db.get_bind().dialect.name != "postgresql":
        return None
    size_bytes = db.execute(text("SELECT pg_database_size(current_database())")).scalar()
    return size_bytes / (1024 * 1024)


def check_database_size(
    db: Session,
    trainers: Iterable[Trainer],
    today: date,
    size_mb: Optional[float] = None,
) -> int:
    """Adds and commits STORAGE_LOW alerts when the database passes 80% / 95% of its limit."""
    limit = settings.DATABASE_SIZE_LIMIT_MB
    if limit <= 0:
        return 0
    if size_mb is None:
        size_mb = database_size_mb(db)
    if size_mb is None:
        return 0

    percent = size_mb / limit * 100
    level = next(((lvl, sev) for lvl, sev in LEVELS if percent >= lvl), None)
    if level is None:
        return 0
    threshold, severity = level

    dedupe_key = f"storage_low:{threshold}:{today.strftime('%Y-%m')}"
    created = 0
    for trainer in trainers:
        if trainer.user_id is None:
            continue
        exists = (
            db.query(Notification.id)
            .filter(Notification.user_id == trainer.user_id, Notification.dedupe_key == dedupe_key)
            .first()
        )
        if exists:
            continue
        db.add(
            Notification(
                user_id=trainer.user_id,
                trainer_id=trainer.id,
                client_id=None,
                type=NotificationType.STORAGE_LOW.value,
                severity=severity.value,
                title=f"Database {percent:.0f}% full",
                message=(
                    f"The database is using {size_mb:.0f} of {limit} MB. Client photos are stored "
                    "there, and once it is full the app can't save changes. Permanently delete "
                    "archived clients you no longer need, or upgrade the database plan."
                ),
                dedupe_key=dedupe_key,
                is_read=False,
            )
        )
        created += 1
    if created:
        db.commit()
        logger.warning("Database at %.0f%% of %s MB; trainer alerted", percent, limit)
    return created
