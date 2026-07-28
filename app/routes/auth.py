from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import templates
from app.schemas.schemas import UserCreate, UserLogin
from app.services.auth_service import (
    authenticate_user,
    create_jwt_token,
    create_user,
    validate_location,
)

# Configure router
router = APIRouter(prefix="/auth", tags=["auth"])

# ==========================================
# REGISTER ROUTES
# ==========================================

@router.get("/register", response_class=HTMLResponse)
async def get_register(request: Request):
    """
    Render the register.html page.
    """
    # Renders the register page
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "request": request
        }
    )


@router.post("/register", response_class=HTMLResponse)
async def post_register(
    request: Request,
    user_data: Annotated[UserCreate, Form()]
):
    """
    Register a new user.
    """
    # Check if the user location is valid
    if not await validate_location(user_data.state, user_data.city):
        raise HTTPException(status_code=400, detail="Invalid state or city.")

    # If valid, try to INSERT user in the database
    try:
        await create_user(user_data.name, user_data.email, user_data.phone_number, user_data.password, user_data.cpf, user_data.state, user_data.city)
    except ValueError:
        raise HTTPException(status_code=409, detail="Email or phone number already registered.")

    # Flash message
    request.session["flash"] = "User registered successfully!"

    # Redirect user to login
    return RedirectResponse(url="/auth/login", status_code=303)

# ==========================================
# LOGIN ROUTES
# ==========================================

@router.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    """
    Render the login.html page.
    """
    # Renders the login page
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request
        }
    )


@router.post("/login", response_class=HTMLResponse)
async def post_login(
    request: Request,
    user: Annotated[UserLogin, Form()]
):
    """
    Authenticate a user and set JWT cookie.
    """
    # Authenticate the user
    auth_user = await authenticate_user(user.email, user.phone_number, user.password)

    # If the response is None, auth failed, raise 401
    if auth_user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials. Retype login info.")

    # Else, create a JWT token for user access
    token = create_jwt_token(auth_user["id"])

    # Add token to a cookie and redirect to homepage "/" with a flash message
    request.session["flash"] = "Logged in successfully!"
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response


# ==========================================
# LOGOUT ROUTE
# ==========================================

@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """
    Logout the user by deleting the JWT cookie.
    """
    # Delete the JWT token and cookie, then redirects to homepage "/" with a flash message
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    request.session["flash"] = "Successfully logged out."
    request.session["flash_type"] = "info"
    return response
