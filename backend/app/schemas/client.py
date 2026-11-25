from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class ClientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None
    age: Optional[int] = Field(None, ge=10, le=120)
    gender: Optional[str] = Field(None, max_length=50)
    height: Optional[float] = Field(None, gt=0, le=300)  # cm
    current_weight: Optional[float] = Field(None, gt=0, le=500)  # kg
    fitness_goal: Optional[str] = "General Fitness"
    status: Optional[str] = "Active"
    profile_photo: Optional[str] = None
    emergency_contact: Optional[str] = Field(None, max_length=100)
    joined_date: Optional[date] = None
    training_preferences: Optional[str] = None


class ClientCreate(ClientBase):
    email: Optional[EmailStr] = None  # optional: clients don't sign in

    @field_validator("email", mode="before")
    @classmethod
    def _blank_email_is_none(cls, v):
        return None if isinstance(v, str) and not v.strip() else v


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    date_of_birth: Optional[date] = None
    age: Optional[int] = Field(None, ge=10, le=120)
    gender: Optional[str] = Field(None, max_length=50)
    height: Optional[float] = Field(None, gt=0, le=300)
    current_weight: Optional[float] = Field(None, gt=0, le=500)
    fitness_goal: Optional[str] = None
    status: Optional[str] = None
    profile_photo: Optional[str] = None
    emergency_contact: Optional[str] = Field(None, max_length=100)
    joined_date: Optional[date] = None
    training_preferences: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def _blank_email_is_none(cls, v):
        return None if isinstance(v, str) and not v.strip() else v


class ClientResponse(ClientBase):
    id: int
    user_id: int
    trainer_id: Optional[int] = None
    email: Optional[EmailStr] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientListItem(ClientResponse):
    # OVERDUE: a fee is past its grace period; DUE: a fee is due now; CLEAR: nothing due;
    # NO_PLAN: no membership plan and no fees
    payment_status: str = "NO_PLAN"
    outstanding_amount: float = 0.0


class PaginatedClientResponse(BaseModel):
    items: List[ClientListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
