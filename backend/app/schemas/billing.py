from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

PAYMENT_METHOD_PATTERN = "^(CASH|UPI|CARD|BANK_TRANSFER|OTHER)$"
Money = Decimal


def _strip(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None


# ---------- Plans ----------

class MembershipPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: Money = Field(..., gt=0, max_digits=10, decimal_places=2)
    duration_months: int = Field(1, ge=1, le=24)
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Plan name cannot be blank")
        return v

    @field_validator("description")
    @classmethod
    def _description(cls, v: Optional[str]) -> Optional[str]:
        return _strip(v)


class MembershipPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[Money] = Field(None, gt=0, max_digits=10, decimal_places=2)
    duration_months: Optional[int] = Field(None, ge=1, le=24)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Plan name cannot be blank")
        return v


class MembershipPlanResponse(BaseModel):
    id: int
    name: str
    price: float
    duration_months: int
    description: Optional[str] = None
    is_active: bool
    client_count: int = 0
    created_at: datetime


# ---------- Client membership ----------

class ClientMembershipUpdate(BaseModel):
    plan_id: int
    fee_amount: Optional[Money] = Field(None, gt=0, max_digits=10, decimal_places=2)
    billing_start_date: Optional[date] = None


class ClientMembershipInfo(BaseModel):
    client_id: int
    client_name: str
    client_phone: Optional[str] = None
    client_status: str
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    duration_months: Optional[int] = None
    fee_amount: Optional[float] = None
    billing_start_date: Optional[date] = None
    next_due_date: Optional[date] = None
    outstanding_amount: float = 0.0
    overdue_count: int = 0


class PaginatedMemberships(BaseModel):
    items: List[ClientMembershipInfo]
    total: int
    page: int
    page_size: int
    total_pages: int
    currency: str


# ---------- Fees & payments ----------

class PaymentCreate(BaseModel):
    amount: Money = Field(..., gt=0, max_digits=10, decimal_places=2)
    paid_on: Optional[date] = None
    method: str = Field("CASH", pattern=PAYMENT_METHOD_PATTERN)
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("reference", "notes")
    @classmethod
    def _text(cls, v: Optional[str]) -> Optional[str]:
        return _strip(v)


class PaymentResponse(BaseModel):
    id: int
    fee_id: int
    amount: float
    paid_on: date
    method: str
    reference: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: Optional[str] = None
    created_at: datetime


class FeeUpdate(BaseModel):
    amount_due: Optional[Money] = Field(None, gt=0, max_digits=10, decimal_places=2)
    due_date: Optional[date] = None
    is_waived: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)


class FeeResponse(BaseModel):
    id: int
    client_id: int
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    plan_name: Optional[str] = None
    period_start: date
    period_end: date
    due_date: date
    amount_due: float
    amount_paid: float
    balance: float
    status: str
    is_waived: bool
    notes: Optional[str] = None
    days_overdue: int = 0
    payments: List[PaymentResponse] = []
    reminder_whatsapp_link: Optional[str] = None


class PaginatedFees(BaseModel):
    items: List[FeeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    currency: str


class ClientFeeAccount(BaseModel):
    membership: ClientMembershipInfo
    fees: List[FeeResponse]
    total_paid: float
    currency: str


class FeeSummary(BaseModel):
    month: str
    month_name: str
    currency: str
    billed_amount: float
    collected_amount: float  # payments received during the month (any period)
    collected_for_month_dues: float
    collection_rate: float  # % of this month's dues already paid
    fees_due_count: int
    paid_count: int
    unpaid_count: int
    outstanding_total: float  # all-time, as of today
    overdue_total: float
    overdue_count: int
    clients_without_plan: int
