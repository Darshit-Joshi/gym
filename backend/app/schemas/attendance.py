from datetime import date as dt_date, datetime as dt_datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AttendanceCreate(BaseModel):
    client_id: int
    date: dt_date
    status: str = Field(default="PRESENT", pattern="^(PRESENT|ABSENT|LATE)$")
    notes: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: int
    client_id: int
    client_name: Optional[str] = None
    client_photo: Optional[str] = None
    trainer_id: int
    date: dt_date
    day_name: str
    formatted_date: str
    attendance_time: Optional[str] = None
    status: str
    notes: Optional[str] = None
    recorded_by_name: Optional[str] = None
    last_modified_by_name: Optional[str] = None
    last_modified_time: Optional[str] = None
    created_at: dt_datetime
    updated_at: dt_datetime

    model_config = {"from_attributes": True}


class DailyAttendanceClientItem(BaseModel):
    client_id: int
    client_name: str
    client_photo: Optional[str] = None
    status: Optional[str] = None  # None indicates UNMARKED
    notes: Optional[str] = None
    attendance_id: Optional[int] = None
    membership_status: str = "Active"
    attendance_time: Optional[str] = None
    day_name: Optional[str] = None
    formatted_date: Optional[str] = None
    recorded_by_name: Optional[str] = None
    last_modified_by_name: Optional[str] = None
    last_modified_time: Optional[str] = None
    created_at: Optional[dt_datetime] = None
    updated_at: Optional[dt_datetime] = None


class DailyAttendanceResponse(BaseModel):
    date: dt_date
    day_name: str
    formatted_date: str
    present_count: int
    absent_count: int
    late_count: int
    unmarked_count: int
    total_clients: int
    clients: List[DailyAttendanceClientItem]


class AttendanceHistorySummary(BaseModel):
    total_recorded: int
    present_count: int
    absent_count: int
    late_count: int
    attendance_percentage: float
    records: List[AttendanceResponse]


class MonthlyClientOverviewItem(BaseModel):
    client_id: int
    client_name: str
    client_photo: Optional[str] = None
    membership_status: str = "Active"
    present_count: int
    absent_count: int
    late_count: int
    total_recorded: int
    attendance_percentage: float


class MonthlyAttendanceOverviewResponse(BaseModel):
    month: str  # YYYY-MM
    month_name: str
    total_clients: int
    page: int
    page_size: int
    total_pages: int
    clients: List[MonthlyClientOverviewItem]
