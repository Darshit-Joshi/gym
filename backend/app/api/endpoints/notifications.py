from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.core.timezone import now_utc
from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.schemas.notification import NotificationResponse, PaginatedNotifications, UnreadCount
from app.services.alerts import whatsapp_link

router = APIRouter()


def _to_response(n: Notification) -> NotificationResponse:
    if n.type == NotificationType.FEE_OVERDUE.value:
        link = "/fees"
    else:
        link = f"/clients/{n.client_id}" if n.client_id else None
    return NotificationResponse(
        id=n.id,
        type=n.type,
        severity=n.severity,
        title=n.title,
        message=n.message,
        is_read=n.is_read,
        created_at=n.created_at,
        read_at=n.read_at,
        client_id=n.client_id,
        client_name=n.client.name if n.client else None,
        fee_id=n.fee_id,
        link=link,
        whatsapp_link=whatsapp_link(n.client.phone if n.client else None, n.client_message),
    )


def _own(db: Session, user: User):
    return db.query(Notification).filter(Notification.user_id == user.id)


@router.get("", response_model=PaginatedNotifications)
def list_notifications(
    unread_only: bool = Query(False),
    type_filter: Optional[NotificationType] = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _own(db, current_user)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    if type_filter is not None:
        query = query.filter(Notification.type == type_filter.value)
    total = query.count()
    items = (
        query.options(joinedload(Notification.client))
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    unread = _own(db, current_user).filter(Notification.is_read.is_(False)).count()
    return PaginatedNotifications(
        items=[_to_response(n) for n in items],
        total=total,
        unread_count=unread,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UnreadCount(count=_own(db, current_user).filter(Notification.is_read.is_(False)).count())


@router.post("/read-all", response_model=UnreadCount)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _own(db, current_user).filter(Notification.is_read.is_(False)).update(
        {Notification.is_read: True, Notification.read_at: now_utc()}, synchronize_session=False
    )
    db.commit()
    return UnreadCount(count=0)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = _own(db, current_user).filter(Notification.id == notification_id).first()
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if not n.is_read:
        n.is_read = True
        n.read_at = now_utc()
        db.commit()
        db.refresh(n)
    return _to_response(n)
