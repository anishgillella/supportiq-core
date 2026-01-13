from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import UserRegister, UserLogin, TokenResponse, UserResponse
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    TokenData,
)
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register a new user and return JWT token"""
    supabase = get_supabase_admin()

    # Check if user already exists
    existing = supabase.table("supportiq_users").select("id").eq("email", user_data.email).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Hash password and create user
    password_hash = get_password_hash(user_data.password)

    user_record = {
        "email": user_data.email,
        "password_hash": password_hash,
        "current_step": 1,
        "onboarding_completed": False,
    }

    # Add company info if provided
    if user_data.company_name:
        user_record["company_name"] = user_data.company_name
    if user_data.company_website:
        user_record["company_website"] = user_data.company_website

    result = supabase.table("supportiq_users").insert(user_record).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    user = result.data[0]

    # Create user profile entry
    supabase.table("supportiq_user_profiles").insert({"user_id": user["id"]}).execute()

    # Generate token
    access_token = create_access_token(data={"sub": user["id"], "email": user["email"]})

    return TokenResponse(access_token=access_token, user_id=user["id"])


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Authenticate user and return JWT token"""
    supabase = get_supabase_admin()

    # Find user by email
    result = (
        supabase.table("supportiq_users")
        .select("id, email, password_hash")
        .eq("email", user_data.email)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = result.data[0]

    # Verify password
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate token
    access_token = create_access_token(data={"sub": user["id"], "email": user["email"]})

    return TokenResponse(access_token=access_token, user_id=user["id"])


@router.get("/check-email")
async def check_email(email: str):
    """Check if an email already exists in the system"""
    supabase = get_supabase_admin()

    existing = supabase.table("supportiq_users").select("id").eq("email", email).execute()

    return {"exists": len(existing.data) > 0}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """Get current authenticated user"""
    supabase = get_supabase_admin()

    result = (
        supabase.table("supportiq_users")
        .select("id, email, current_step, onboarding_completed, created_at")
        .eq("id", current_user.user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(**result.data[0])
