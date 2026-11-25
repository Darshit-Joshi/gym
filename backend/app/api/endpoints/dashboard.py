from datetime import timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_trainer, get_db
from app.api.endpoints.attendance import daily_roster_filter
from app.core.timezone import today_gym
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.billing import FeePayment, FeeRecord, FeeStatus
from app.models.client import Client, ClientStatus
from app.models.notification import Notification
from app.models.session import WorkoutSession
from app.schemas.client import ClientResponse
from app.schemas.dashboard import (
    ActivityItem,
    AttendanceDashboardSummary,
    AttendanceTrendDay,
    DashboardBillingSummary,
    TrainerDashboardResponse,
    UpcomingDueItem,
)
from app.services.alerts import format_money
from app.services.billing import ZERO, compute_fee_status, money, month_bounds, outstanding, unpaid_clause
from app.services.trainer_settings import get_or_create_settings

router = APIRouter()

UPCOMING_DUE_DAYS = 7
TREND_DAYS = 7
ACTIVITY_LIMIT = 8


@router.get("/trainer", response_model=TrainerDashboardResponse)
def get_trainer_dashboard(
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    today = today_gym()
    prefs = get_or_create_settings(db, trainer.id)

    clients = db.query(Client).filter(Client.trainer_id == trainer.id)
    total_clients = clients.count()
    active_clients = clients.filter(Client.status == ClientStatus.ACTIVE.value).count()
    roster_count = db.query(Client).filter(*daily_roster_filter(trainer.id, today)).count()

    # Today's attendance (same roster as the daily attendance sheet)
    counts = dict(
        db.query(AttendanceRecord.status, func.count(AttendanceRecord.id))
        .join(Client, Client.id == AttendanceRecord.client_id)
        .filter(
            AttendanceRecord.trainer_id == trainer.id,
            AttendanceRecord.date == today,
            Client.status != ClientStatus.ARCHIVED.value,
        )
        .group_by(AttendanceRecord.status)
        .all()
    )
    present = counts.get(AttendanceStatus.PRESENT.value, 0)
    absent = counts.get(AttendanceStatus.ABSENT.value, 0)
    late = counts.get(AttendanceStatus.LATE.value, 0)
    today_attendance = AttendanceDashboardSummary(
        present=present,
        absent=absent,
        late=late,
        unmarked=max(0, roster_count - present - absent - late),
    )

    # Fees
    unpaid = (
        db.query(FeeRecord)
        .join(Client, Client.id == FeeRecord.client_id)
        .filter(FeeRecord.trainer_id == trainer.id, unpaid_clause(), Client.status != ClientStatus.ARCHIVED.value)
        .order_by(FeeRecord.due_date.asc())
        .all()
    )
    statuses = {f.id: compute_fee_status(f, today, prefs.fee_grace_days) for f in unpaid}
    overdue = [f for f in unpaid if statuses[f.id] == FeeStatus.OVERDUE]
    first, last = month_bounds(today.year, today.month)
    collected = (
        db.query(func.coalesce(func.sum(FeePayment.amount), 0))
        .filter(FeePayment.trainer_id == trainer.id, FeePayment.paid_on >= first, FeePayment.paid_on <= last)
        .scalar()
    )
    unread_alerts = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == trainer.user_id, Notification.is_read.is_(False))
        .scalar()
        or 0
    )
    billing = DashboardBillingSummary(
        currency=prefs.currency,
        outstanding_total=float(sum((outstanding(f) for f in unpaid), ZERO)),
        overdue_total=float(sum((outstanding(f) for f in overdue), ZERO)),
        overdue_count=len(overdue),
        collected_this_month=float(money(collected)),
        unread_alerts=unread_alerts,
    )

    # Dues that are due now (within grace) or in the next week
    horizon = today + timedelta(days=UPCOMING_DUE_DAYS)
    upcoming_dues = [
        UpcomingDueItem(
            fee_id=f.id,
            client_id=f.client_id,
            client_name=f.client.name,
            due_date=f.due_date,
            balance=float(outstanding(f)),
            status=statuses[f.id].value,
        )
        for f in unpaid
        if statuses[f.id] != FeeStatus.OVERDUE and f.due_date <= horizon
    ][:8]

    recent_clients = [
        ClientResponse.model_validate(c)
        for c in clients.order_by(Client.created_at.desc()).limit(5).all()
    ]

    return TrainerDashboardResponse(
        attendance_trend=_attendance_trend(db, trainer.id, today),
        recent_activity=_recent_activity(db, trainer.id, prefs.currency),
        total_clients=total_clients,
        active_clients=active_clients,
        today_attendance=today_attendance,
        billing=billing,
        upcoming_dues=upcoming_dues,
        recent_clients=recent_clients,
    )


def _attendance_trend(db: Session, trainer_id: int, today) -> list:
    """Check-ins and absences per day for the last TREND_DAYS days, oldest first."""
    start = today - timedelta(days=TREND_DAYS - 1)
    rows = (
        db.query(AttendanceRecord.date, AttendanceRecord.status, func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.trainer_id == trainer_id,
            AttendanceRecord.date >= start,
            AttendanceRecord.date <= today,
        )
        .group_by(AttendanceRecord.date, AttendanceRecord.status)
        .all()
    )
    by_day = {start + timedelta(days=i): {"in": 0, "absent": 0} for i in range(TREND_DAYS)}
    for day, st, n in rows:
        if day not in by_day:
            continue
        if st == AttendanceStatus.ABSENT.value:
            by_day[day]["absent"] += n
        else:
            by_day[day]["in"] += n
    return [AttendanceTrendDay(date=d, checked_in=v["in"], absent=v["absent"]) for d, v in sorted(by_day.items())]


def _recent_activity(db: Session, trainer_id: int, currency: str) -> list:
    """Latest check-ins, payments, logged workouts and new clients, newest first."""
    items = []
    checkins = (
        db.query(AttendanceRecord, Client)
        .join(Client, Client.id == AttendanceRecord.client_id)
        .filter(AttendanceRecord.trainer_id == trainer_id, AttendanceRecord.status != AttendanceStatus.ABSENT.value)
        .order_by(AttendanceRecord.created_at.desc())
        .limit(ACTIVITY_LIMIT)
        .all()
    )
    for rec, c in checkins:
        label = "Checked in late" if rec.status == AttendanceStatus.LATE.value else "Checked in"
        items.append(ActivityItem(kind="ATTENDANCE", client_id=c.id, client_name=c.name, client_photo=c.profile_photo,
                                  date=rec.date, at=rec.created_at, detail=label))

    payments = (
        db.query(FeePayment, Client)
        .join(Client, Client.id == FeePayment.client_id)
        .filter(FeePayment.trainer_id == trainer_id)
        .order_by(FeePayment.created_at.desc())
        .limit(ACTIVITY_LIMIT)
        .all()
    )
    for p, c in payments:
        items.append(ActivityItem(kind="PAYMENT", client_id=c.id, client_name=c.name, client_photo=c.profile_photo,
                                  date=p.paid_on, at=p.created_at, detail=f"Paid {format_money(p.amount, currency)}"))

    workouts = (
        db.query(WorkoutSession, Client)
        .join(Client, Client.id == WorkoutSession.client_id)
        .filter(WorkoutSession.trainer_id == trainer_id)
        .order_by(WorkoutSession.updated_at.desc())
        .limit(ACTIVITY_LIMIT)
        .all()
    )
    for w, c in workouts:
        n = len(w.session_exercises)
        detail = f"{w.workout_name or 'Workout'} · {n} exercise{'' if n == 1 else 's'}"
        items.append(ActivityItem(kind="WORKOUT", client_id=c.id, client_name=c.name, client_photo=c.profile_photo,
                                  date=w.date, at=w.updated_at, detail=detail))

    new_clients = (
        db.query(Client)
        .filter(Client.trainer_id == trainer_id)
        .order_by(Client.created_at.desc())
        .limit(ACTIVITY_LIMIT)
        .all()
    )
    for c in new_clients:
        items.append(ActivityItem(kind="CLIENT_ADDED", client_id=c.id, client_name=c.name, client_photo=c.profile_photo,
                                  date=c.joined_date or c.created_at.date(), at=c.created_at, detail="Joined as a client"))

    def sort_key(item):
        at = item.at
        return at.replace(tzinfo=None) if at.tzinfo is None else at.astimezone(timezone.utc).replace(tzinfo=None)

    return sorted(items, key=sort_key, reverse=True)[:ACTIVITY_LIMIT]
