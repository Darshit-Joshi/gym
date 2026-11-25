"""Trainer alerts: absence streaks, monthly absences and overdue fees.

Every alert carries a dedupe key, so these functions are safe to call repeatedly
(on every attendance write and on every scheduler tick).
"""
import re
from datetime import date, timedelta
from typing import List, Optional
from urllib.parse import quote

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.billing import FeeRecord
from app.models.client import Client, ClientStatus
from app.models.notification import Notification, NotificationSeverity, NotificationType
from app.models.trainer import Trainer
from app.models.trainer_settings import TrainerSettings
from app.services.billing import money, outstanding, unpaid_clause

# How many recent attendance rows to scan when measuring an absence streak
STREAK_SCAN_LIMIT = 62


def format_money(amount, currency: str) -> str:
    value = money(amount)
    text = f"{int(value):,}" if value == value.to_integral() else f"{value:,.2f}"
    symbol = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(currency.upper())
    return f"{symbol}{text}" if symbol else f"{currency.upper()} {text}"


def whatsapp_link(phone: Optional[str], text: Optional[str]) -> Optional[str]:
    if not phone or not text:
        return None
    digits = re.sub(r"\D", "", phone)
    if phone.strip().startswith("00"):
        digits = digits[2:]
    if len(digits) == 10 and app_settings.DEFAULT_PHONE_COUNTRY_CODE:
        digits = f"{app_settings.DEFAULT_PHONE_COUNTRY_CODE}{digits}"
    if len(digits) < 8 or len(digits) > 15:
        return None
    return f"https://wa.me/{digits}?text={quote(text)}"


def create_notification(
    db: Session,
    *,
    trainer: Trainer,
    client: Client,
    ntype: NotificationType,
    severity: NotificationSeverity,
    title: str,
    message: str,
    dedupe_key: str,
    client_message: Optional[str] = None,
    fee_id: Optional[int] = None,
) -> Optional[Notification]:
    """Adds a trainer notification unless one with the same dedupe key exists. Does NOT commit."""
    if trainer.user_id is None:
        return None
    exists = (
        db.query(Notification.id)
        .filter(Notification.user_id == trainer.user_id, Notification.dedupe_key == dedupe_key)
        .first()
    )
    if exists:
        return None
    for pending in db.new:
        if isinstance(pending, Notification) and pending.user_id == trainer.user_id and pending.dedupe_key == dedupe_key:
            return None
    n = Notification(
        user_id=trainer.user_id,
        trainer_id=trainer.id,
        client_id=client.id,
        fee_id=fee_id,
        type=ntype.value,
        severity=severity.value,
        title=title[:200],
        message=message,
        client_message=client_message,
        dedupe_key=dedupe_key[:150],
        is_read=False,
    )
    db.add(n)
    return n


def current_absence_streak(db: Session, client_id: int) -> tuple[int, Optional[date]]:
    """Counts consecutive ABSENT records, most recent first. Unmarked days are ignored
    (the gym may not run every day); any PRESENT/LATE record ends the streak.
    Returns (streak_length, date_streak_started)."""
    rows = (
        db.query(AttendanceRecord.date, AttendanceRecord.status)
        .filter(AttendanceRecord.client_id == client_id)
        .order_by(AttendanceRecord.date.desc())
        .limit(STREAK_SCAN_LIMIT)
        .all()
    )
    streak = 0
    started: Optional[date] = None
    for row_date, row_status in rows:
        if (row_status or "").upper() != AttendanceStatus.ABSENT.value:
            break
        streak += 1
        started = row_date
    return streak, started


def evaluate_client_absence(
    db: Session,
    client: Client,
    trainer: Trainer,
    prefs: TrainerSettings,
    today: date,
) -> List[Notification]:
    """Raises absence alerts for one client. Does NOT commit."""
    if client.status != ClientStatus.ACTIVE.value:
        return []
    created: List[Notification] = []
    first_name = (client.name or "there").split(" ")[0]

    streak, started = current_absence_streak(db, client.id)
    if streak >= prefs.absence_streak_threshold and started is not None:
        n = create_notification(
            db, trainer=trainer, client=client,
            ntype=NotificationType.ABSENCE_STREAK, severity=NotificationSeverity.WARNING,
            title=f"{client.name} missed {streak} sessions in a row",
            message=f"{client.name} has been marked absent for {streak} consecutive sessions "
                    f"(since {started.strftime('%d %b %Y')}).",
            dedupe_key=f"absence_streak:{client.id}:{started.isoformat()}",
            client_message=(
                f"Hi {first_name}, we've missed you at the gym for your last {streak} sessions. "
                "Is everything okay? Let us know if you need to adjust your schedule."
            ),
        )
        if n:
            created.append(n)

    month_absences = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.client_id == client.id,
            AttendanceRecord.status == AttendanceStatus.ABSENT.value,
            extract("year", AttendanceRecord.date) == today.year,
            extract("month", AttendanceRecord.date) == today.month,
        )
        .scalar()
        or 0
    )
    if month_absences >= prefs.absence_monthly_threshold:
        month_label = today.strftime("%B %Y")
        n = create_notification(
            db, trainer=trainer, client=client,
            ntype=NotificationType.ABSENCE_MONTHLY, severity=NotificationSeverity.WARNING,
            title=f"{client.name}: {month_absences} absences in {month_label}",
            message=f"{client.name} has reached {month_absences} absences this month.",
            dedupe_key=f"absence_monthly:{client.id}:{today.strftime('%Y-%m')}",
            client_message=(
                f"Hi {first_name}, you've missed {month_absences} sessions so far in {month_label}. "
                "Consistency is key to reaching your goals. See you at the next session!"
            ),
        )
        if n:
            created.append(n)
    return created


def evaluate_fee_alerts(db: Session, trainer: Trainer, prefs: TrainerSettings, today: date) -> int:
    """Raises one alert per fee that is unpaid past the grace period. Commits."""
    overdue_cutoff = today - timedelta(days=prefs.fee_grace_days)
    fees = (
        db.query(FeeRecord)
        .join(Client, Client.id == FeeRecord.client_id)
        .filter(
            FeeRecord.trainer_id == trainer.id,
            unpaid_clause(),
            FeeRecord.due_date < overdue_cutoff,
            Client.status != ClientStatus.ARCHIVED.value,
        )
        .all()
    )
    count = 0
    for fee in fees:
        client = fee.client
        balance = format_money(outstanding(fee), prefs.currency)
        period = f"{fee.period_start.strftime('%d %b')} – {fee.period_end.strftime('%d %b %Y')}"
        first_name = (client.name or "there").split(" ")[0]
        n = create_notification(
            db, trainer=trainer, client=client, fee_id=fee.id,
            ntype=NotificationType.FEE_OVERDUE, severity=NotificationSeverity.CRITICAL,
            title=f"{client.name}: fee of {balance} overdue",
            message=f"Fee for {period} was due on {fee.due_date.strftime('%d %b %Y')}. Outstanding: {balance}.",
            dedupe_key=f"fee_overdue:{fee.id}",
            client_message=(
                f"Hi {first_name}, a friendly reminder that your gym fee of {balance} "
                f"for {period} was due on {fee.due_date.strftime('%d %b %Y')}. "
                "Please clear it at your earliest convenience."
            ),
        )
        count += 1 if n else 0
    db.commit()
    return count
