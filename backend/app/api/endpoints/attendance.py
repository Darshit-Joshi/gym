import logging
from datetime import date as dt_date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import extract, or_, select
from app.api.deps import (
    get_db,
    get_current_user,
    get_current_trainer,
    verify_client_access,
)
from app.models.user import User, UserRole
from app.models.trainer import Trainer
from app.models.client import Client, ClientStatus
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.core.timezone import (
    today_gym,
    now_utc,
    format_time,
    format_full_date,
    get_weekday,
    format_month_name,
)
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceResponse,
    DailyAttendanceClientItem,
    DailyAttendanceResponse,
    AttendanceHistorySummary,
    MonthlyClientOverviewItem,
    MonthlyAttendanceOverviewResponse,
)

from app.services.alerts import evaluate_client_absence
from app.services.trainer_settings import get_or_create_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Clients who appear on the daily sheet: everyone currently training, plus anyone
# (e.g. a since-deactivated client) who already has a record for that day.
ROSTER_STATUSES = (ClientStatus.ACTIVE.value, ClientStatus.PENDING_ACTIVATION.value)


def daily_roster_filter(trainer_id: int, target_date: dt_date):
    """SQL filter on Client for the daily attendance roster of one trainer."""
    has_record_that_day = Client.id.in_(
        select(AttendanceRecord.client_id).where(
            AttendanceRecord.trainer_id == trainer_id,
            AttendanceRecord.date == target_date,
        )
    )
    return (
        Client.trainer_id == trainer_id,
        Client.status != ClientStatus.ARCHIVED.value,
        or_(Client.status.in_(ROSTER_STATUSES), has_record_that_day),
    )


def _raise_absence_alerts(db: Session, client: Client) -> None:
    """Checks absence thresholds right after attendance changes. Never fails the request."""
    try:
        trainer = db.query(Trainer).filter(Trainer.id == client.trainer_id).first() if client.trainer_id else None
        if trainer is None:
            return
        prefs = get_or_create_settings(db, trainer.id)
        created = evaluate_client_absence(db, client, trainer, prefs, today_gym())
        if created:
            db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to evaluate absence alerts for client %s", client.id)


def _format_attendance_response(record: AttendanceRecord) -> AttendanceResponse:
    recorder_name = None
    if record.recorder:
        recorder_name = record.recorder.email

    last_modifier_name = None
    if record.last_modifier:
        last_modifier_name = record.last_modifier.email

    return AttendanceResponse(
        id=record.id,
        client_id=record.client_id,
        client_name=record.client.name if record.client else None,
        client_photo=record.client.profile_photo if record.client else None,
        trainer_id=record.trainer_id,
        date=record.date,
        day_name=get_weekday(record.date),
        formatted_date=format_full_date(record.date),
        attendance_time=format_time(record.created_at),
        status=record.status,
        notes=record.notes,
        recorded_by_name=recorder_name,
        last_modified_by_name=last_modifier_name,
        last_modified_time=format_time(record.updated_at),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=DailyAttendanceResponse)
def get_daily_attendance(
    attendance_date: Optional[dt_date] = Query(None, description="Target date, defaults to today in gym timezone"),
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    """
    Returns daily attendance sheet for all clients assigned to the authenticated trainer on a selected date.
    Clearly distinguishes marked (Present, Absent, Late) from unmarked clients,
    with complete timestamps and weekday names in the configured gym timezone.
    """
    _, trainer = trainer_data
    target_date = attendance_date or today_gym()
    day_name = get_weekday(target_date)
    formatted_date = format_full_date(target_date)

    clients = (
        db.query(Client)
        .filter(*daily_roster_filter(trainer.id, target_date))
        .order_by(Client.name.asc())
        .all()
    )

    # Get all attendance records for this trainer on target_date
    records = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.trainer_id == trainer.id,
            AttendanceRecord.date == target_date,
        )
        .all()
    )
    record_map = {r.client_id: r for r in records}

    client_items = []
    present_count = 0
    absent_count = 0
    late_count = 0
    unmarked_count = 0

    for c in clients:
        rec = record_map.get(c.id)
        if rec:
            rec_status = rec.status.upper()
            if rec_status == AttendanceStatus.PRESENT.value:
                present_count += 1
            elif rec_status == AttendanceStatus.ABSENT.value:
                absent_count += 1
            elif rec_status == AttendanceStatus.LATE.value:
                late_count += 1

            client_items.append(
                DailyAttendanceClientItem(
                    client_id=c.id,
                    client_name=c.name,
                    client_photo=c.profile_photo,
                    status=rec_status,
                    notes=rec.notes,
                    attendance_id=rec.id,
                    membership_status=c.status,
                    attendance_time=format_time(rec.created_at),
                    day_name=day_name,
                    formatted_date=formatted_date,
                    recorded_by_name=rec.recorder.email if rec.recorder else None,
                    last_modified_by_name=rec.last_modifier.email if rec.last_modifier else None,
                    last_modified_time=format_time(rec.updated_at),
                    created_at=rec.created_at,
                    updated_at=rec.updated_at,
                )
            )
        else:
            unmarked_count += 1
            client_items.append(
                DailyAttendanceClientItem(
                    client_id=c.id,
                    client_name=c.name,
                    client_photo=c.profile_photo,
                    status=None,  # Unmarked
                    notes=None,
                    attendance_id=None,
                    membership_status=c.status,
                    attendance_time=None,
                    day_name=day_name,
                    formatted_date=formatted_date,
                    recorded_by_name=None,
                    last_modified_by_name=None,
                    last_modified_time=None,
                    created_at=None,
                    updated_at=None,
                )
            )

    return DailyAttendanceResponse(
        date=target_date,
        day_name=day_name,
        formatted_date=formatted_date,
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        unmarked_count=unmarked_count,
        total_clients=len(clients),
        clients=client_items,
    )


@router.get("/monthly-overview", response_model=MonthlyAttendanceOverviewResponse)
def get_monthly_attendance_overview(
    month: Optional[str] = Query(None, description="Target month in YYYY-MM format, defaults to current month"),
    search: Optional[str] = Query(None, description="Search client name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    """
    Returns monthly attendance overview across all clients assigned to the authenticated trainer.
    Includes present/absent/late counts, attendance percentage, and pagination.
    Strictly enforces trainer data isolation.
    """
    _, trainer = trainer_data

    # Determine target year and month
    if not month:
        now_d = today_gym()
        yr, mo = now_d.year, now_d.month
        month_str = f"{yr:04d}-{mo:02d}"
    else:
        try:
            parts = month.strip().split("-")
            if len(parts) == 2:
                yr, mo = int(parts[0]), int(parts[1])
                if not (1 <= mo <= 12):
                    raise ValueError()
                month_str = f"{yr:04d}-{mo:02d}"
            else:
                raise ValueError()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month format, expected YYYY-MM (e.g. 2026-10)",
            )

    month_name = format_month_name(yr, mo)

    # Filter active clients of this trainer with optional search
    client_query = db.query(Client).filter(
        Client.trainer_id == trainer.id,
        Client.status != ClientStatus.ARCHIVED.value,
    )
    if search and search.strip():
        client_query = client_query.filter(Client.name.ilike(f"%{search.strip()}%"))

    total_clients = client_query.count()
    total_pages = max(1, (total_clients + page_size - 1) // page_size)

    clients = (
        client_query.order_by(Client.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    if not clients:
        return MonthlyAttendanceOverviewResponse(
            month=month_str,
            month_name=month_name,
            total_clients=total_clients,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            clients=[],
        )

    client_ids = [c.id for c in clients]

    # Query attendance records for these clients in target month
    records = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.trainer_id == trainer.id,
            AttendanceRecord.client_id.in_(client_ids),
            extract("year", AttendanceRecord.date) == yr,
            extract("month", AttendanceRecord.date) == mo,
        )
        .all()
    )

    # Aggregate by client_id
    stats_by_client = {cid: {"PRESENT": 0, "ABSENT": 0, "LATE": 0} for cid in client_ids}
    for r in records:
        st = r.status.upper() if r.status else "PRESENT"
        if r.client_id in stats_by_client and st in stats_by_client[r.client_id]:
            stats_by_client[r.client_id][st] += 1

    client_items = []
    for c in clients:
        c_stats = stats_by_client.get(c.id, {"PRESENT": 0, "ABSENT": 0, "LATE": 0})
        pres = c_stats["PRESENT"]
        abse = c_stats["ABSENT"]
        late = c_stats["LATE"]
        tot = pres + abse + late
        pct = round(((pres + late) / tot) * 100, 1) if tot > 0 else 0.0

        client_items.append(
            MonthlyClientOverviewItem(
                client_id=c.id,
                client_name=c.name,
                client_photo=c.profile_photo,
                membership_status=c.status,
                present_count=pres,
                absent_count=abse,
                late_count=late,
                total_recorded=tot,
                attendance_percentage=pct,
            )
        )

    return MonthlyAttendanceOverviewResponse(
        month=month_str,
        month_name=month_name,
        total_clients=total_clients,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        clients=client_items,
    )


@router.post("", response_model=AttendanceResponse)
def record_attendance(
    att_in: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Records or updates attendance for a client on a specific date.
    - If a record already exists, updates the status/notes and last_modified_by_user_id,
      strictly PRESERVING the original created_at timestamp and original recorded_by_user_id.
    - If a new record is created, sets both created_at, updated_at, and recorded_by_user_id.
    - Enforces uniqueness constraint and trainer ownership.
    """
    client = verify_client_access(att_in.client_id, current_user, db)
    if att_in.date > today_gym():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance cannot be marked for a future date",
        )

    trainer_id = client.trainer_id
    if current_user.role == UserRole.TRAINER.value:
        trainer = db.query(Trainer).filter(Trainer.user_id == current_user.id).first()
        if trainer:
            trainer_id = trainer.id

    now_val = now_utc()

    # Check for existing record on this client and date
    existing = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.client_id == client.id,
            AttendanceRecord.date == att_in.date,
        )
        .first()
    )

    if existing:
        existing.status = att_in.status.upper()
        if att_in.notes is not None:
            existing.notes = att_in.notes
        existing.last_modified_by_user_id = current_user.id
        existing.updated_at = now_val
        # Note: existing.created_at and existing.recorded_by_user_id are strictly preserved!
        db.commit()
        db.refresh(existing)
        if existing.status == AttendanceStatus.ABSENT.value:
            _raise_absence_alerts(db, client)
            db.refresh(existing)
        return _format_attendance_response(existing)

    new_rec = AttendanceRecord(
        client_id=client.id,
        trainer_id=trainer_id,
        date=att_in.date,
        status=att_in.status.upper(),
        notes=att_in.notes,
        recorded_by_user_id=current_user.id,
        last_modified_by_user_id=current_user.id,
        created_at=now_val,
        updated_at=now_val,
    )
    db.add(new_rec)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent request (e.g. a double tap) created this client's record for the
        # day first. The unique constraint kept one row; apply this status to it.
        db.rollback()
        existing = (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.client_id == client.id, AttendanceRecord.date == att_in.date)
            .one()
        )
        existing.status = att_in.status.upper()
        if att_in.notes is not None:
            existing.notes = att_in.notes
        existing.last_modified_by_user_id = current_user.id
        existing.updated_at = now_utc()
        db.commit()
        new_rec = existing
    db.refresh(new_rec)
    if new_rec.status == AttendanceStatus.ABSENT.value:
        _raise_absence_alerts(db, client)
        db.refresh(new_rec)
    return _format_attendance_response(new_rec)


@router.get("/client/{client_id}", response_model=AttendanceHistorySummary)
def get_client_attendance_history(
    client_id: int,
    date: Optional[dt_date] = Query(None, description="Exact single date filter"),
    start_date: Optional[dt_date] = Query(None, description="Start date filter"),
    end_date: Optional[dt_date] = Query(None, description="End date filter"),
    month: Optional[str] = Query(None, description="Month filter (YYYY-MM format)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Status filter (PRESENT, ABSENT, LATE)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns attendance history for a single client with comprehensive filters:
    - Exact date
    - Date range (start_date, end_date)
    - Month (YYYY-MM format)
    - Attendance status (PRESENT, ABSENT, LATE)
    Returns accurate summary counts and full formatted timestamps/day names.
    """
    client = verify_client_access(client_id, current_user, db)

    query = db.query(AttendanceRecord).filter(AttendanceRecord.client_id == client.id)

    if date:
        query = query.filter(AttendanceRecord.date == date)
    if start_date:
        query = query.filter(AttendanceRecord.date >= start_date)
    if end_date:
        query = query.filter(AttendanceRecord.date <= end_date)
    if month:
        try:
            parts = month.strip().split("-")
            if len(parts) == 2:
                yr, mo = int(parts[0]), int(parts[1])
                query = query.filter(
                    extract("year", AttendanceRecord.date) == yr,
                    extract("month", AttendanceRecord.date) == mo,
                )
            else:
                raise ValueError("Invalid format")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month format, expected YYYY-MM (e.g. 2026-10)",
            )
    if status_filter:
        query = query.filter(AttendanceRecord.status == status_filter.upper())

    records = query.order_by(AttendanceRecord.date.desc(), AttendanceRecord.id.desc()).all()

    present_count = sum(1 for r in records if r.status.upper() == AttendanceStatus.PRESENT.value)
    absent_count = sum(1 for r in records if r.status.upper() == AttendanceStatus.ABSENT.value)
    late_count = sum(1 for r in records if r.status.upper() == AttendanceStatus.LATE.value)
    total_recorded = len(records)

    attendance_percentage = (
        round(((present_count + late_count) / total_recorded) * 100, 1)
        if total_recorded > 0
        else 0.0
    )

    return AttendanceHistorySummary(
        total_recorded=total_recorded,
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        attendance_percentage=attendance_percentage,
        records=[_format_attendance_response(r) for r in records],
    )


@router.delete("/{attendance_id}")
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    trainer_data=Depends(get_current_trainer),
):
    """
    Deletes an attendance record. Enforces trainer ownership.
    """
    _, trainer = trainer_data
    record = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.id == attendance_id,
            AttendanceRecord.trainer_id == trainer.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendance record with id {attendance_id} not found",
        )

    db.delete(record)
    db.commit()
    return {"message": "Attendance record deleted successfully"}
