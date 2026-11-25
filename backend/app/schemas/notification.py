from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    type: str
    severity: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    fee_id: Optional[int] = None
    link: Optional[str] = None
    whatsapp_link: Optional[str] = None


class PaginatedNotifications(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
    total_pages: int


class UnreadCount(BaseModel):
    count: int
