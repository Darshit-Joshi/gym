from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.client import ClientResponse


class AttendanceDashboardSummary(BaseModel):
    present: int = 0
    absent: int = 0
    late: int = 0
    unmarked: int = 0


class DashboardBillingSummary(BaseModel):
    currency: str = "INR"
    outstanding_total: float = 0.0
    overdue_total: float = 0.0
    overdue_count: int = 0
    collected_this_month: float = 0.0
    unread_alerts: int = 0


class UpcomingDueItem(BaseModel):
    fee_id: int
    client_id: int
    client_name: str
    due_date: date
    balance: float
    status: str


class AttendanceTrendDay(BaseModel):
    date: date
    checked_in: int  # present + late
    absent: int


class ActivityItem(BaseModel):
    kind: str  # ATTENDANCE | PAYMENT | WORKOUT | CLIENT_ADDED
    client_id: int
    client_name: str
    client_photo: Optional[str] = None
    date: date
    at: datetime
    detail: str


class TrainerDashboardResponse(BaseModel):
    total_clients: int
    active_clients: int
    today_attendance: AttendanceDashboardSummary
    billing: DashboardBillingSummary
    upcoming_dues: List[UpcomingDueItem]
    recent_clients: List[ClientResponse]
    attendance_trend: List[AttendanceTrendDay] = []
    recent_activity: List[ActivityItem] = []
