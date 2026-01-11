from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# Request models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    company_name: Optional[str] = None
    company_website: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Response models
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class UserResponse(BaseModel):
    id: str
    email: str
    current_step: int
    onboarding_completed: bool
    created_at: datetime


class ProfileResponse(BaseModel):
    about_me: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    birthdate: Optional[str] = None


class UserWithProfileResponse(BaseModel):
    id: str
    email: str
    current_step: int
    onboarding_completed: bool
    created_at: datetime
    profile: Optional[ProfileResponse] = None


# Progress models
class ProgressUpdate(BaseModel):
    step: int
    about_me: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    birthdate: Optional[str] = None


class ProgressResponse(BaseModel):
    current_step: int
    onboarding_completed: bool
    profile: Optional[ProfileResponse] = None
