from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_trainer, get_current_user, get_db, verify_client_access
from app.core.timezone import format_month_name, today_gym
from app.models.billing import FeePayment, FeeRecord, FeeStatus, MembershipPlan
from app.models.client import Client, ClientStatus
from app.models.user import User
from app.models.trainer_settings import TrainerSettings
from app.schemas.billing import (
    ClientFeeAccount,
    ClientMembershipInfo,
    ClientMembershipUpdate,
    FeeResponse,
    FeeSummary,
    FeeUpdate,
    MembershipPlanCreate,
    MembershipPlanResponse,
    MembershipPlanUpdate,
    PaginatedFees,
    PaginatedMemberships,
    PaymentCreate,
    PaymentResponse,
)
from app.services.alerts import format_money, whatsapp_link
from app.services.billing import (
    ZERO,
    add_months,
    client_search_clause,
    compute_fee_status,
    generate_dues_for_client,
    month_bounds,
    money,
    next_due_date,
    outstanding,
    parse_month,
    recalculate_amount_paid,
    status_filter_clause,
    unpaid_clause,
)
from app.services.trainer_settings import get_or_create_settings

router = APIRouter()


# ---------------------------------------------------------------- helpers

def _parse_month_or_400(month: Optional[str], today: date):
    try:
        return parse_month(month, today)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid month format, expected YYYY-MM (e.g. 2026-10)",
        )


def _plan_response(plan: MembershipPlan, client_count: int = 0) -> MembershipPlanResponse:
    return MembershipPlanResponse(
        id=plan.id,
        name=plan.name,
        price=float(money(plan.price)),
        duration_months=plan.duration_months,
        description=plan.description,
        is_active=plan.is_active,
        client_count=client_count,
        created_at=plan.created_at,
    )


def _payment_response(p: FeePayment) -> PaymentResponse:
    return PaymentResponse(
        id=p.id,
        fee_id=p.fee_id,
        amount=float(money(p.amount)),
        paid_on=p.paid_on,
        method=p.method,
        reference=p.reference,
        notes=p.notes,
        recorded_by=p.recorder.email if p.recorder else None,
        created_at=p.created_at,
    )


def _fee_response(
    fee: FeeRecord,
    prefs: TrainerSettings,
    today: date,
    include_payments: bool = True,
) -> FeeResponse:
    fee_status = compute_fee_status(fee, today, prefs.fee_grace_days)
    balance = outstanding(fee)
    days_overdue = max(0, (today - fee.due_date).days) if balance > ZERO and fee.due_date < today else 0
    reminder = None
    if balance > ZERO and fee.client is not None:
        first = (fee.client.name or "there").split(" ")[0]
        text = (
            f"Hi {first}, a gentle reminder that your gym fee of {format_money(balance, prefs.currency)} "
            f"for {fee.period_start.strftime('%d %b')} – {fee.period_end.strftime('%d %b %Y')} "
            f"{'was' if fee.due_date < today else 'is'} due on {fee.due_date.strftime('%d %b %Y')}. Thank you!"
        )
        reminder = whatsapp_link(fee.client.phone, text)
    return FeeResponse(
        id=fee.id,
        client_id=fee.client_id,
        client_name=fee.client.name if fee.client else None,
        client_phone=fee.client.phone if fee.client else None,
        plan_name=fee.plan_name,
        period_start=fee.period_start,
        period_end=fee.period_end,
        due_date=fee.due_date,
        amount_due=float(money(fee.amount_due)),
        amount_paid=float(money(fee.amount_paid)),
        balance=float(balance),
        status=fee_status.value,
        is_waived=fee.is_waived,
        notes=fee.notes,
        days_overdue=days_overdue,
        payments=[_payment_response(p) for p in fee.payments] if include_payments else [],
        reminder_whatsapp_link=reminder,
    )


def _membership_info(db: Session, client: Client, prefs: TrainerSettings, today: date) -> ClientMembershipInfo:
    plan = client.membership_plan
    fees = db.query(FeeRecord).filter(FeeRecord.client_id == client.id, unpaid_clause()).all()
    total_outstanding = sum((outstanding(f) for f in fees), ZERO)
    overdue = sum(1 for f in fees if compute_fee_status(f, today, prefs.fee_grace_days) == FeeStatus.OVERDUE)
    return ClientMembershipInfo(
        client_id=client.id,
        client_name=client.name,
        client_phone=client.phone,
        client_status=client.status,
        plan_id=plan.id if plan else None,
        plan_name=plan.name if plan else None,
        duration_months=plan.duration_months if plan else None,
        fee_amount=float(money(client.fee_amount)) if client.fee_amount is not None and plan else None,
        billing_start_date=client.billing_start_date if plan else None,
        next_due_date=next_due_date(db, client, today) if plan or fees else None,
        outstanding_amount=float(total_outstanding),
        overdue_count=overdue,
    )


def _get_trainer_fee(db: Session, fee_id: int, trainer_id: int, lock: bool = False) -> FeeRecord:
    query = db.query(FeeRecord).filter(FeeRecord.id == fee_id, FeeRecord.trainer_id == trainer_id)
    if lock:
        query = query.with_for_update()
    fee = query.first()
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fee record {fee_id} not found")
    return fee


def _client_account(db: Session, client: Client) -> ClientFeeAccount:
    today = today_gym()
    prefs = get_or_create_settings(db, client.trainer_id) if client.trainer_id else None
    if prefs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client has no assigned trainer")
    fees = (
        db.query(FeeRecord)
        .options(selectinload(FeeRecord.payments))
        .filter(FeeRecord.client_id == client.id)
        .order_by(FeeRecord.due_date.desc())
        .all()
    )
    total_paid = sum((money(f.amount_paid) for f in fees), ZERO)
    return ClientFeeAccount(
        membership=_membership_info(db, client, prefs, today),
        fees=[_fee_response(f, prefs, today) for f in fees],
        total_paid=float(total_paid),
        currency=prefs.currency,
    )


# ---------------------------------------------------------------- plans

@router.get("/plans", response_model=List[MembershipPlanResponse])
def list_plans(
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    query = db.query(MembershipPlan).filter(MembershipPlan.trainer_id == trainer.id)
    if not include_inactive:
        query = query.filter(MembershipPlan.is_active.is_(True))
    plans = query.order_by(MembershipPlan.is_active.desc(), MembershipPlan.price.asc()).all()
    counts = dict(
        db.query(Client.membership_plan_id, func.count(Client.id))
        .filter(Client.trainer_id == trainer.id, Client.membership_plan_id.isnot(None))
        .group_by(Client.membership_plan_id)
        .all()
    )
    return [_plan_response(p, counts.get(p.id, 0)) for p in plans]


@router.post("/plans", response_model=MembershipPlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    plan_in: MembershipPlanCreate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    duplicate = (
        db.query(MembershipPlan.id)
        .filter(MembershipPlan.trainer_id == trainer.id, func.lower(MembershipPlan.name) == plan_in.name.lower())
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A plan with this name already exists")
    plan = MembershipPlan(
        trainer_id=trainer.id,
        name=plan_in.name,
        price=money(plan_in.price),
        duration_months=plan_in.duration_months,
        description=plan_in.description,
        is_active=True,
    )
    db.add(plan)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A plan with this name already exists")
    db.refresh(plan)
    return _plan_response(plan)


@router.put("/plans/{plan_id}", response_model=MembershipPlanResponse)
def update_plan(
    plan_id: int,
    plan_in: MembershipPlanUpdate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    """Updating a plan affects future dues only; existing fee records keep their amounts."""
    _, trainer = trainer_data
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id, MembershipPlan.trainer_id == trainer.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    data = plan_in.model_dump(exclude_unset=True)
    if "name" in data and data["name"].lower() != plan.name.lower():
        dup = (
            db.query(MembershipPlan.id)
            .filter(
                MembershipPlan.trainer_id == trainer.id,
                func.lower(MembershipPlan.name) == data["name"].lower(),
                MembershipPlan.id != plan.id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A plan with this name already exists")
    for field, value in data.items():
        setattr(plan, field, money(value) if field == "price" else value)
    db.commit()
    db.refresh(plan)
    count = db.query(func.count(Client.id)).filter(Client.membership_plan_id == plan.id).scalar() or 0
    return _plan_response(plan, count)


@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == plan_id, MembershipPlan.trainer_id == trainer.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    in_use = db.query(func.count(Client.id)).filter(Client.membership_plan_id == plan.id).scalar() or 0
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Plan is assigned to {in_use} client(s). Reassign them or deactivate the plan instead.",
        )
    db.delete(plan)
    db.commit()
    return {"message": "Plan deleted"}


# ---------------------------------------------------------------- memberships

@router.get("/memberships", response_model=PaginatedMemberships)
def list_memberships(
    search: Optional[str] = Query(None, max_length=100),
    has_plan: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    prefs = get_or_create_settings(db, trainer.id)
    today = today_gym()
    query = db.query(Client).filter(Client.trainer_id == trainer.id, Client.status != ClientStatus.ARCHIVED.value)
    clause = client_search_clause(search)
    if clause is not None:
        query = query.filter(clause)
    if has_plan is True:
        query = query.filter(Client.membership_plan_id.isnot(None))
    elif has_plan is False:
        query = query.filter(Client.membership_plan_id.is_(None))
    total = query.count()
    clients = query.order_by(Client.name.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedMemberships(
        items=[_membership_info(db, c, prefs, today) for c in clients],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
        currency=prefs.currency,
    )


@router.put("/clients/{client_id}/membership", response_model=ClientFeeAccount)
def assign_membership(
    client_id: int,
    body: ClientMembershipUpdate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    """Assigns (or changes) a client's plan. Dues for periods that have already started are
    generated immediately; later periods are generated automatically by the scheduler."""
    user, trainer = trainer_data
    client = verify_client_access(client_id, user, db)
    if client.status == ClientStatus.ARCHIVED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot bill an archived client")
    plan = db.query(MembershipPlan).filter(MembershipPlan.id == body.plan_id, MembershipPlan.trainer_id == trainer.id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if not plan.is_active and client.membership_plan_id != plan.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This plan is inactive")

    today = today_gym()
    start = body.billing_start_date or client.billing_start_date or today
    if start > add_months(today, 12):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing start date cannot be more than a year ahead")
    if start < add_months(today, -24):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing start date is too far in the past")

    client.membership_plan_id = plan.id
    client.fee_amount = money(body.fee_amount if body.fee_amount is not None else plan.price)
    client.billing_start_date = start
    db.flush()
    db.refresh(client)
    prefs = get_or_create_settings(db, trainer.id)
    try:
        generate_dues_for_client(db, client, today, lookahead_days=prefs.fee_reminder_days)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Billing was updated concurrently, please retry")
    db.refresh(client)
    return _client_account(db, client)


@router.delete("/clients/{client_id}/membership", response_model=ClientFeeAccount)
def stop_membership(
    client_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    """Stops future billing. Existing dues and payments are kept."""
    user, _ = trainer_data
    client = verify_client_access(client_id, user, db)
    client.membership_plan_id = None
    client.fee_amount = None
    client.billing_start_date = None
    db.commit()
    db.refresh(client)
    return _client_account(db, client)


@router.get("/clients/{client_id}", response_model=ClientFeeAccount)
def get_client_fee_account(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = verify_client_access(client_id, current_user, db)
    return _client_account(db, client)


# ---------------------------------------------------------------- dues

@router.get("/summary", response_model=FeeSummary)
def fee_summary(
    month: Optional[str] = Query(None, description="YYYY-MM, defaults to current month"),
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    prefs = get_or_create_settings(db, trainer.id)
    today = today_gym()
    yr, mo = _parse_month_or_400(month, today)
    first, last = month_bounds(yr, mo)

    month_fees = (
        db.query(FeeRecord)
        .filter(
            FeeRecord.trainer_id == trainer.id,
            FeeRecord.due_date >= first,
            FeeRecord.due_date <= last,
            FeeRecord.is_waived.is_(False),
        )
        .all()
    )
    billed = sum((money(f.amount_due) for f in month_fees), ZERO)
    paid_for_month = sum((min(money(f.amount_paid), money(f.amount_due)) for f in month_fees), ZERO)
    paid_count = sum(1 for f in month_fees if money(f.amount_paid) >= money(f.amount_due))

    collected = (
        db.query(func.coalesce(func.sum(FeePayment.amount), 0))
        .filter(FeePayment.trainer_id == trainer.id, FeePayment.paid_on >= first, FeePayment.paid_on <= last)
        .scalar()
    )

    unpaid = db.query(FeeRecord).filter(FeeRecord.trainer_id == trainer.id, unpaid_clause()).all()
    outstanding_total = sum((outstanding(f) for f in unpaid), ZERO)
    overdue = [f for f in unpaid if compute_fee_status(f, today, prefs.fee_grace_days) == FeeStatus.OVERDUE]

    no_plan = (
        db.query(func.count(Client.id))
        .filter(
            Client.trainer_id == trainer.id,
            Client.membership_plan_id.is_(None),
            Client.status.in_([ClientStatus.ACTIVE.value, ClientStatus.PENDING_ACTIVATION.value]),
        )
        .scalar()
        or 0
    )

    return FeeSummary(
        month=f"{yr:04d}-{mo:02d}",
        month_name=format_month_name(yr, mo),
        currency=prefs.currency,
        billed_amount=float(billed),
        collected_amount=float(money(collected)),
        collected_for_month_dues=float(paid_for_month),
        collection_rate=round(float(paid_for_month / billed * 100), 1) if billed > ZERO else 0.0,
        fees_due_count=len(month_fees),
        paid_count=paid_count,
        unpaid_count=len(month_fees) - paid_count,
        outstanding_total=float(outstanding_total),
        overdue_total=float(sum((outstanding(f) for f in overdue), ZERO)),
        overdue_count=len(overdue),
        clients_without_plan=no_plan,
    )


@router.get("", response_model=PaginatedFees)
def list_fees(
    month: Optional[str] = Query(None, description="Filter by due month YYYY-MM"),
    status_filter: Optional[FeeStatus] = Query(None, alias="status"),
    unpaid_only: bool = Query(False),
    client_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    prefs = get_or_create_settings(db, trainer.id)
    today = today_gym()

    query = (
        db.query(FeeRecord)
        .join(Client, Client.id == FeeRecord.client_id)
        .options(selectinload(FeeRecord.payments))
        .filter(FeeRecord.trainer_id == trainer.id)
    )
    if month:
        yr, mo = _parse_month_or_400(month, today)
        first, last = month_bounds(yr, mo)
        query = query.filter(FeeRecord.due_date >= first, FeeRecord.due_date <= last)
    if status_filter is not None:
        query = query.filter(status_filter_clause(status_filter, today, prefs.fee_grace_days))
    if unpaid_only:
        query = query.filter(unpaid_clause())
    if client_id is not None:
        query = query.filter(FeeRecord.client_id == client_id)
    clause = client_search_clause(search)
    if clause is not None:
        query = query.filter(clause)

    total = query.count()
    fees = (
        query.order_by(FeeRecord.due_date.desc(), Client.name.asc(), FeeRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedFees(
        items=[_fee_response(f, prefs, today) for f in fees],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
        currency=prefs.currency,
    )


@router.patch("/{fee_id}", response_model=FeeResponse)
def update_fee(
    fee_id: int,
    body: FeeUpdate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    """Adjust the amount or due date, add a note, or waive/un-waive a fee."""
    _, trainer = trainer_data
    fee = _get_trainer_fee(db, fee_id, trainer.id, lock=True)
    data = body.model_dump(exclude_unset=True)
    if "amount_due" in data and data["amount_due"] is not None:
        new_due = money(data["amount_due"])
        if new_due < money(fee.amount_paid):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount due cannot be less than the amount already paid",
            )
        fee.amount_due = new_due
    if data.get("due_date") is not None:
        fee.due_date = data["due_date"]
    if data.get("is_waived") is not None:
        fee.is_waived = data["is_waived"]
    if "notes" in data:
        fee.notes = (data["notes"] or "").strip() or None
    db.commit()
    db.refresh(fee)
    prefs = get_or_create_settings(db, trainer.id)
    return _fee_response(fee, prefs, today_gym())


@router.delete("/{fee_id}")
def delete_fee(
    fee_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    fee = _get_trainer_fee(db, fee_id, trainer.id)
    if fee.payments:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This fee has payments recorded. Delete the payments first or waive the fee instead.",
        )
    db.delete(fee)
    db.commit()
    return {"message": "Fee record deleted"}


# ---------------------------------------------------------------- payments

@router.post("/{fee_id}/payments", response_model=FeeResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    fee_id: int,
    body: PaymentCreate,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    user, trainer = trainer_data
    fee = _get_trainer_fee(db, fee_id, trainer.id, lock=True)
    today = today_gym()
    if fee.is_waived:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This fee has been waived")
    amount = money(body.amount)
    balance = outstanding(fee)
    if balance <= ZERO:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This fee is already fully paid")
    if amount > balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment exceeds the outstanding balance of {balance}",
        )
    paid_on = body.paid_on or today
    if paid_on > today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment date cannot be in the future")

    db.add(
        FeePayment(
            fee_id=fee.id,
            client_id=fee.client_id,
            trainer_id=trainer.id,
            amount=amount,
            paid_on=paid_on,
            method=body.method,
            reference=body.reference,
            notes=body.notes,
            recorded_by_user_id=user.id,
        )
    )
    db.flush()
    recalculate_amount_paid(db, fee)
    db.commit()
    db.refresh(fee)
    prefs = get_or_create_settings(db, trainer.id)
    return _fee_response(fee, prefs, today)


@router.delete("/payments/{payment_id}", response_model=FeeResponse)
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    _, trainer = trainer_data
    payment = (
        db.query(FeePayment)
        .filter(FeePayment.id == payment_id, FeePayment.trainer_id == trainer.id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    fee = _get_trainer_fee(db, payment.fee_id, trainer.id, lock=True)
    db.delete(payment)
    db.flush()
    recalculate_amount_paid(db, fee)
    db.commit()
    db.refresh(fee)
    prefs = get_or_create_settings(db, trainer.id)
    return _fee_response(fee, prefs, today_gym())
