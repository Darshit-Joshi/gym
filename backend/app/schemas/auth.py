from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    name: str
    trainer_id: Optional[int] = None
    client_id: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class RegisterTrainerRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (minimum 8 characters)")
    phone: Optional[str] = Field(None, max_length=50, description="Optional phone number")


SetupTrainerRequest = RegisterTrainerRequest


class SetupStatusResponse(BaseModel):
    is_setup_completed: bool
    has_trainer: bool
    can_register_trainer: bool


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    profile_image: Optional[str] = None


class ResetTrainerPasswordRequest(BaseModel):
    recovery_key: str
    email: EmailStr
    new_password: str = Field(..., min_length=8)
