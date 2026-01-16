from fastapi import APIRouter, HTTPException
from typing import List
from app.models.user import UserWithProfileResponse, ProfileResponse
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/supportiq_users", tags=["Users"])


@router.get("", response_model=List[UserWithProfileResponse])
async def get_all_supportiq_users():
    """Get all supportiq_users with their profiles (public endpoint for data table)"""
    supabase = get_supabase_admin()

    # Get all supportiq_users
    supportiq_users_result = (
        supabase.table("supportiq_users")
        .select("id, email, current_step, onboarding_completed, created_at")
        .order("created_at", desc=True)
        .execute()
    )

    if not supportiq_users_result.data:
        return []

    # Get all profiles
    user_ids = [user["id"] for user in supportiq_users_result.data]
    profiles_result = (
        supabase.table("supportiq_user_profiles")
        .select("user_id, about_me, street_address, city, state, zip_code, birthdate")
        .in_("user_id", user_ids)
        .execute()
    )

    # Create profile lookup
    profiles_by_user = {}
    for profile in profiles_result.data or []:
        profiles_by_user[profile["user_id"]] = ProfileResponse(
            about_me=profile.get("about_me"),
            street_address=profile.get("street_address"),
            city=profile.get("city"),
            state=profile.get("state"),
            zip_code=profile.get("zip_code"),
            birthdate=profile.get("birthdate"),
        )

    # Combine supportiq_users with profiles
    result = []
    for user in supportiq_users_result.data:
        result.append(
            UserWithProfileResponse(
                id=user["id"],
                email=user["email"],
                current_step=user["current_step"],
                onboarding_completed=user["onboarding_completed"],
                created_at=user["created_at"],
                profile=profiles_by_user.get(user["id"]),
            )
        )

    return result


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete a user by ID (admin endpoint)"""
    supabase = get_supabase_admin()

    # First check if user exists
    user_result = (
        supabase.table("supportiq_users")
        .select("id, email")
        .eq("id", user_id)
        .execute()
    )

    if not user_result.data:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete user (profile will be cascade deleted due to ON DELETE CASCADE)
    supabase.table("supportiq_users").delete().eq("id", user_id).execute()

    return {"message": f"User {user_result.data[0]['email']} deleted successfully"}


@router.delete("/by-email/{email}")
async def delete_user_by_email(email: str):
    """Delete a user by email (admin endpoint)"""
    supabase = get_supabase_admin()

    # First find the user
    user_result = (
        supabase.table("supportiq_users")
        .select("id, email")
        .eq("email", email)
        .execute()
    )

    if not user_result.data:
        raise HTTPException(status_code=404, detail=f"User with email {email} not found")

    user_id = user_result.data[0]["id"]

    # Delete user (profile will be cascade deleted due to ON DELETE CASCADE)
    supabase.table("supportiq_users").delete().eq("id", user_id).execute()

    return {"message": f"User {email} deleted successfully"}
