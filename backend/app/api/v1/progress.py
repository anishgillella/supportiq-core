from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import ProgressUpdate, ProgressResponse, ProfileResponse
from app.core.security import get_current_user, TokenData
from app.core.database import get_supabase_admin

router = APIRouter(prefix="/progress", tags=["Onboarding Progress"])


@router.get("", response_model=ProgressResponse)
async def get_progress(current_user: TokenData = Depends(get_current_user)):
    """Get user's current onboarding progress and profile data"""
    supabase = get_supabase_admin()

    # Get user data
    user_result = (
        supabase.table("supportiq_users")
        .select("current_step, onboarding_completed")
        .eq("id", current_user.user_id)
        .execute()
    )

    if not user_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user = user_result.data[0]

    # Get profile data
    profile_result = (
        supabase.table("supportiq_user_profiles")
        .select("about_me, street_address, city, state, zip_code, birthdate")
        .eq("user_id", current_user.user_id)
        .execute()
    )

    profile = None
    if profile_result.data:
        profile_data = profile_result.data[0]
        profile = ProfileResponse(
            about_me=profile_data.get("about_me"),
            street_address=profile_data.get("street_address"),
            city=profile_data.get("city"),
            state=profile_data.get("state"),
            zip_code=profile_data.get("zip_code"),
            birthdate=profile_data.get("birthdate"),
        )

    return ProgressResponse(
        current_step=user["current_step"],
        onboarding_completed=user["onboarding_completed"],
        profile=profile,
    )


@router.put("", response_model=dict)
async def update_progress(
    data: ProgressUpdate, current_user: TokenData = Depends(get_current_user)
):
    """Update user's onboarding progress and profile data"""
    supabase = get_supabase_admin()

    # Update user's current step
    supabase.table("supportiq_users").update({"current_step": data.step}).eq(
        "id", current_user.user_id
    ).execute()

    # Build profile update data
    profile_update = {}
    if data.about_me is not None:
        profile_update["about_me"] = data.about_me
    if data.street_address is not None:
        profile_update["street_address"] = data.street_address
    if data.city is not None:
        profile_update["city"] = data.city
    if data.state is not None:
        profile_update["state"] = data.state
    if data.zip_code is not None:
        profile_update["zip_code"] = data.zip_code
    if data.birthdate is not None:
        profile_update["birthdate"] = data.birthdate

    # Update profile if there's data to update
    if profile_update:
        # Check if profile exists
        existing = (
            supabase.table("supportiq_user_profiles")
            .select("id")
            .eq("user_id", current_user.user_id)
            .execute()
        )

        if existing.data:
            supabase.table("supportiq_user_profiles").update(profile_update).eq(
                "user_id", current_user.user_id
            ).execute()
        else:
            profile_update["user_id"] = current_user.user_id
            supabase.table("supportiq_user_profiles").insert(profile_update).execute()

    return {"success": True}


@router.post("/complete", response_model=dict)
async def complete_onboarding(current_user: TokenData = Depends(get_current_user)):
    """Mark onboarding as complete"""
    supabase = get_supabase_admin()

    supabase.table("supportiq_users").update({"onboarding_completed": True}).eq(
        "id", current_user.user_id
    ).execute()

    return {"success": True}
