from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import templates
from app.schemas.schemas import UserUpdate
from app.services.auth_service import (
    get_user_by_id,
    verify_user_token,
)
from app.services.user_service import (
    check_email_exists,
    check_phone_exists,
    delete_user,
    update_user,
)

# Configure router
router = APIRouter(prefix="/users", tags=["users"])

# ==========================================
# USER PROFILE ROUTES
# ==========================================

@router.get("/profile", response_class=HTMLResponse)
async def get_profile(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Render user profile page (requires login).
    """
    user_data = await get_user_by_id(user_id)

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found or doesn't exist")

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user_data,
            "user_id": user_id
        }
    )


# ==========================================
# USER EDIT ROUTES
# ==========================================

@router.get("/profile/edit", response_class=HTMLResponse)
async def get_edit_profile(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Render user edit profile page (requires login).
    """
    # Get user info
    user_data = await get_user_by_id(user_id)

    # If user isn't found, return 404
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found or doesn't found.")

    # Render the profile edit form(?) page
    return templates.TemplateResponse(
        request,
        "edit_profile.html",
        {
            "request": request,
            "user": user_data,
            "user_id": user_id
        }
    )


@router.post("/profile/edit", response_class=HTMLResponse)
async def post_edit_profile(
    request: Request,
    user_id: int = Depends(verify_user_token),
    user_data: Annotated[UserUpdate, Form()] = None
):
    """
    Update user profile data (requires login).
    """
    # Get current user info
    current_user = await get_user_by_id(user_id)

    # If the user is changing their email to a new one, check if that new email is already registered
    if user_data.email and user_data.email != current_user["email"] and await check_email_exists(user_data.email, exclude_user_id=user_id):
        raise HTTPException(status_code=409, detail="This email is already registered.")

    # If the user is changing their phone number to a new one, check if that new phone number is already registered
    if user_data.phone_number and user_data.phone_number != current_user["phone_number"] and await check_phone_exists(user_data.phone_number, exclude_user_id=user_id):
        raise HTTPException(status_code=409, detail="This phone number is already registered.")

    # Else, update the account info
    try:
        await update_user(user_id,
                          name=user_data.name,
                          email=user_data.email,
                          phone_number=user_data.phone_number,
                          state=user_data.state,
                          city=user_data.city,
                          password=user_data.password)
    except ValueError:
        raise HTTPException(status_code=409, detail="New email or phone number is already registered.")

    # Flash message
    request.session["flash"] = "Account profile information successfully updated."

    # Redirect back to profile
    return RedirectResponse(url="/users/profile", status_code=303)
    

# ==========================================
# USER SETTINGS ROUTES (OPTIONAL)
# ==========================================

@router.get("/settings", response_class=HTMLResponse)
async def get_settings(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Render user settings page (requires login).
    """
    # Get user info
    user_data = await get_user_by_id(user_id)

    # If user isn't found, return 404
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found or doesn't found.")

    # Render settings page with user info
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "request": request,
            "user": user_data,
            "user_id": user_id
        }
    )

@router.post("/settings/delete-account", response_class=HTMLResponse)
async def delete_account(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Delete user account (requires login).
    """
    # Delete user
    is_deleted = await delete_user(user_id)

    # If the deletion went well, delete the user's access token, display a flash message and redirect to login
    if is_deleted:
        request.session["flash"] = "Account successfully deleted."
        response = RedirectResponse(url="/auth/login", status_code=303)
        response.delete_cookie(key="access_token")
    else:
        # Else, something with the server stopped the deletion, return 500
        raise HTTPException(status_code=500, detail="It was not possible to delete your account at this time. Please try again later.")

    return response
