"""Billing domain logic: billing periods, fee status and dues generation."""
import calendar
import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.billing import FeeRecord, FeeStatus, MembershipPlan
from app.models.client import Client, ClientStatus

logger = logging.getLogger(__name__)

ZERO = Decimal("0.00")
# Safety cap on how many periods are generated for one client in one run
MAX_PERIODS_PER_RUN = 120
BILLABLE_STATUSES = (ClientStatus.ACTIVE.value, ClientStatus.PENDING_ACTIVATION.value)


def money(value) -> Decimal:
    if value is None:
        return ZERO
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def add_months(d: date, months: int) -> date:
    """Adds calendar months, clamping the day (Jan 31 + 1 month -> Feb 28/29)."""
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def billing_period(anchor: date, cycle_months: int, index: int) -> Tuple[date, date]:
    """Returns (start, end) of the index-th period. Computed from the anchor so days never drift."""
    start = add_months(anchor, index * cycle_months)
    end = add_months(anchor, (index + 1) * cycle_months) - timedelta(days=1)
    return start, end


def parse_month(month: Optional[str], default: date) -> Tuple[int, int]:
    """Parses 'YYYY-MM'. Raises ValueError on bad input."""
    if not month:
        return default.year, default.month
    parts = month.strip().split("-")
    if len(parts) != 2:
        raise ValueError("Invalid month format")
    yr, mo = int(parts[0]), int(parts[1])
    if not (1 <= mo <= 12) or not (2000 <= yr <= 2100):
        raise ValueError("Invalid month value")
    return yr, mo


def month_bounds(yr: int, mo: int) -> Tuple[date, date]:
    return date(yr, mo, 1), date(yr, mo, calendar.monthrange(yr, mo)[1])


def outstanding(fee: FeeRecord) -> Decimal:
    if fee.is_waived:
        return ZERO
    return max(ZERO, money(fee.amount_due) - money(fee.amount_paid))


def compute_fee_status(fee: FeeRecord, today: date, grace_days: int) -> FeeStatus:
    if fee.is_waived:
        return FeeStatus.WAIVED
    due = money(fee.amount_due)
    paid = money(fee.amount_paid)
    if paid >= due:
        return FeeStatus.PAID
    if today > fee.due_date + timedelta(days=grace_days):
        return FeeStatus.OVERDUE
    if paid > ZERO:
        return FeeStatus.PARTIAL
    if fee.due_date > today:
        return FeeStatus.UPCOMING
    return FeeStatus.PENDING


def status_filter_clause(status: FeeStatus, today: date, grace_days: int):
    """SQL equivalent of compute_fee_status, for filtering in the database."""
    overdue_cutoff = today - timedelta(days=grace_days)
    not_waived = FeeRecord.is_waived.is_(False)
    unpaid = FeeRecord.amount_paid < FeeRecord.amount_due
    if status == FeeStatus.WAIVED:
        return FeeRecord.is_waived.is_(True)
    if status == FeeStatus.PAID:
        return and_(not_waived, FeeRecord.amount_paid >= FeeRecord.amount_due)
    if status == FeeStatus.OVERDUE:
        return and_(not_waived, unpaid, FeeRecord.due_date < overdue_cutoff)
    if status == FeeStatus.PARTIAL:
        return and_(not_waived, unpaid, FeeRecord.amount_paid > 0, FeeRecord.due_date >= overdue_cutoff)
    if status == FeeStatus.UPCOMING:
        return and_(not_waived, FeeRecord.amount_paid <= 0, FeeRecord.due_date > today)
    if status == FeeStatus.PENDING:
        return and_(
            not_waived,
            FeeRecord.amount_paid <= 0,
            FeeRecord.due_date <= today,
            FeeRecord.due_date >= overdue_cutoff,
        )
    raise ValueError(f"Unknown status {status}")


def unpaid_clause():
    return and_(FeeRecord.is_waived.is_(False), FeeRecord.amount_paid < FeeRecord.amount_due)


def recalculate_amount_paid(db: Session, fee: FeeRecord) -> None:
    from app.models.billing import FeePayment

    total = db.query(func.coalesce(func.sum(FeePayment.amount), 0)).filter(FeePayment.fee_id == fee.id).scalar()
    fee.amount_paid = money(total)


def is_billable(client: Client) -> bool:
    return bool(
        client.membership_plan_id
        and client.fee_amount is not None
        and money(client.fee_amount) > ZERO
        and client.billing_start_date
        and client.status in BILLABLE_STATUSES
        and client.trainer_id
    )


def generate_dues_for_client(
    db: Session,
    client: Client,
    today: date,
    lookahead_days: int = 0,
) -> List[FeeRecord]:
    """Creates fee records for every billing period that has started (or starts within
    `lookahead_days`) and is not yet billed. Idempotent. Does NOT commit."""
    if not is_billable(client):
        return []
    plan: Optional[MembershipPlan] = client.membership_plan
    if plan is None:
        return []
    cycle = max(1, int(plan.duration_months or 1))
    horizon = today + timedelta(days=max(0, lookahead_days))

    last_end = (
        db.query(func.max(FeeRecord.period_end)).filter(FeeRecord.client_id == client.id).scalar()
    )

    created: List[FeeRecord] = []
    for index in range(MAX_PERIODS_PER_RUN * 10):
        start, end = billing_period(client.billing_start_date, cycle, index)
        if start > horizon or len(created) >= MAX_PERIODS_PER_RUN:
            break
        if last_end is not None and start <= last_end:
            continue  # already billed (or overlaps a period billed under an earlier plan)
        fee = FeeRecord(
            client_id=client.id,
            trainer_id=client.trainer_id,
            plan_id=plan.id,
            plan_name=plan.name,
            period_start=start,
            period_end=end,
            due_date=start,
            amount_due=money(client.fee_amount),
            amount_paid=ZERO,
            is_waived=False,
        )
        db.add(fee)
        created.append(fee)
    return created


def generate_dues_for_trainer(db: Session, trainer_id: int, today: date, lookahead_days: int = 0) -> int:
    """Generates dues for all billable clients of a trainer, committing per client so one
    conflicting client never blocks the others. Returns the number of records created."""
    clients = (
        db.query(Client)
        .filter(
            Client.trainer_id == trainer_id,
            Client.membership_plan_id.isnot(None),
            Client.status.in_(BILLABLE_STATUSES),
        )
        .all()
    )
    total = 0
    for client in clients:
        try:
            created = generate_dues_for_client(db, client, today, lookahead_days)
            if created:
                db.commit()
                total += len(created)
        except IntegrityError:
            # A concurrent run inserted the same period first; safe to skip.
            db.rollback()
            logger.info("Skipped duplicate dues generation for client %s", client.id)
    return total


def next_due_date(db: Session, client: Client, today: date) -> Optional[date]:
    """Earliest unpaid due date, or the start of the next unbilled period."""
    unpaid = (
        db.query(func.min(FeeRecord.due_date))
        .filter(FeeRecord.client_id == client.id, unpaid_clause())
        .scalar()
    )
    if unpaid:
        return unpaid
    if not is_billable(client) or client.membership_plan is None:
        return None
    last_end = db.query(func.max(FeeRecord.period_end)).filter(FeeRecord.client_id == client.id).scalar()
    cycle = max(1, int(client.membership_plan.duration_months or 1))
    for index in range(MAX_PERIODS_PER_RUN * 10):
        start, _ = billing_period(client.billing_start_date, cycle, index)
        if last_end is None or start > last_end:
            return start
    return None


def client_search_clause(search: Optional[str]):
    if not search or not search.strip():
        return None
    term = f"%{search.strip()}%"
    return or_(Client.name.ilike(term), Client.phone.ilike(term))
