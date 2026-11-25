"""Periodic maintenance: dues generation and absence/fee alerts.

Run by the in-process scheduler (app.services.scheduler), by the CLI
(`python -m app.cli run-daily-jobs`, e.g. from cron) or on demand by the trainer.
Everything here is idempotent.
"""
import logging
from datetime import date
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.timezone import today_gym
from app.models.client import Client, ClientStatus
from app.models.trainer import Trainer
from app.services.alerts import evaluate_client_absence, evaluate_fee_alerts
from app.services.billing import generate_dues_for_trainer
from app.services.trainer_settings import get_or_create_settings

logger = logging.getLogger(__name__)


def run_daily_jobs(db: Session, today: Optional[date] = None, trainer_id: Optional[int] = None) -> dict:
    today = today or today_gym()
    query = db.query(Trainer)
    if trainer_id is not None:
        query = query.filter(Trainer.id == trainer_id)
    trainers = query.all()

    summary = {"dues_created": 0, "absence_alerts": 0, "fee_alerts": 0}
    for trainer in trainers:
        prefs = get_or_create_settings(db, trainer.id)

        # Bill a few days early so upcoming dues show on the dashboard before the due date
        summary["dues_created"] += generate_dues_for_trainer(
            db, trainer.id, today, lookahead_days=prefs.fee_reminder_days
        )

        clients = (
            db.query(Client)
            .filter(Client.trainer_id == trainer.id, Client.status == ClientStatus.ACTIVE.value)
            .all()
        )
        for client in clients:
            try:
                created = evaluate_client_absence(db, client, trainer, prefs, today)
                if created:
                    db.commit()
                    summary["absence_alerts"] += len(created)
            except IntegrityError:
                db.rollback()

        try:
            summary["fee_alerts"] += evaluate_fee_alerts(db, trainer, prefs, today)
        except IntegrityError:
            db.rollback()

    logger.info("Daily jobs finished for %s: %s", today.isoformat(), summary)
    return summary
