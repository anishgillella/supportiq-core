from fastapi import APIRouter, HTTPException, status
from app.models.config import PageConfig, ConfigResponse
from app.core.database import get_supabase

router = APIRouter(prefix="/admin", tags=["Admin Configuration"])

# Valid component types
VALID_COMPONENTS = {"aboutMe", "address", "birthdate"}


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get current onboarding page configuration"""
    supabase = get_supabase()

    result = (
        supabase.table("onboarding_config")
        .select("page_number, component_type, display_order")
        .order("display_order")
        .execute()
    )

    # Group by page
    page2_components = []
    page3_components = []

    for item in result.data:
        if item["page_number"] == 2:
            page2_components.append(item["component_type"])
        elif item["page_number"] == 3:
            page3_components.append(item["component_type"])

    # Return defaults if no config exists
    if not page2_components:
        page2_components = ["aboutMe", "address"]
    if not page3_components:
        page3_components = ["birthdate"]

    return ConfigResponse(page2=page2_components, page3=page3_components)


@router.put("/config", response_model=dict)
async def update_config(config: PageConfig):
    """Update onboarding page configuration"""
    # Validate components
    all_components = set(config.page2 + config.page3)
    if not all_components.issubset(VALID_COMPONENTS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid component type. Valid types are: {VALID_COMPONENTS}",
        )

    # Validate each page has at least 1 component
    if len(config.page2) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page 2 must have at least 1 component",
        )
    if len(config.page3) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page 3 must have at least 1 component",
        )

    # Validate each page has at most 2 components
    if len(config.page2) > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page 2 can have at most 2 components",
        )
    if len(config.page3) > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page 3 can have at most 2 components",
        )

    supabase = get_supabase()

    # Clear existing config
    supabase.table("onboarding_config").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    # Insert new config
    new_config = []
    for i, component in enumerate(config.page2):
        new_config.append(
            {"page_number": 2, "component_type": component, "display_order": i + 1}
        )
    for i, component in enumerate(config.page3):
        new_config.append(
            {"page_number": 3, "component_type": component, "display_order": i + 1}
        )

    if new_config:
        supabase.table("onboarding_config").insert(new_config).execute()

    return {"success": True}
