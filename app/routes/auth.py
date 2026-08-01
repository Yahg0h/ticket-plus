import re
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text

from app.config import templates
from app.database import engine
from app.schemas.schemas import EMAIL_REGEX, PHONE_REGEX, UserCreate, UserLogin
from app.services.audit_service import (
    get_ip_from_request,
    get_user_agent_from_request,
    log_action,
)
from app.services.auth_service import (
    authenticate_user,
    create_jwt_token,
    create_user,
    decode_token,
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

    # ==== AUDIT LOGS ENTRY: ====
    # Get id of recently created user and log action
    async with engine.connect() as conn:
        query = await conn.execute(text("SELECT id FROM users WHERE id = LAST_INSERT_ID()"))
        recent_id = query.scalar()

    # Add new values to a dict and add log action
    new_values={
        "name": user_data.name,
        "email": user_data.email,
        "phone_number": user_data.phone_number
    }

    # Get IP Address of the request
    ip_address = get_ip_from_request(request)

    # Get User-Agent of the request
    user_agent = get_user_agent_from_request(request)

    # Log action
    await log_action(
        action='create',
        auditable_type='user',
        auditable_id=recent_id,
        user_id=None, 
        old_values=None,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent)
    # ==== END OF AUDIT LOGS ENTRY ====

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
    # Check if the login method is email or phone_number
    # (phone_number also comes in name=email, that's why the check is necessary)
    user_login_method = user.email

    # If it is a email, add None to phone_number; if it is a phone number, add None to email; Else, return 400
    if re.match(EMAIL_REGEX,user_login_method):
        user.email = user_login_method
        user.phone_number = None
    elif re.match(PHONE_REGEX, user_login_method):
        user.email = None
        user.phone_number = user_login_method
    else:
        raise HTTPException(status_code=400, detail="Email or phone number isn't valid. Please try again.")

    # Authenticate the user
    auth_user = await authenticate_user(user.email, user.phone_number, user.password)

    # If the response is None, auth failed, raise 401
    if auth_user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials. Retype login info.")

    # ==== AUDIT LOGS ENTRY: ====
    # Get IP Address of the request
    ip_address = get_ip_from_request(request)

    # Get User-Agent of the request
    user_agent = get_user_agent_from_request(request)

    # Log action
    await log_action(
        action='login',
        auditable_type='user',
        auditable_id=auth_user['id'],
        user_id=auth_user['id'],
        old_values=None,
        new_values=None,
        ip_address=ip_address,
        user_agent=user_agent
    )
    # ==== END OF THE AUDIT LOGS ENTRY ====

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

    # ==== AUDIT LOGS ENTRY: ====
    try:
        # Get the user's session token
        token = request.cookies.get("access_token")

        # Decode the token to get the user's id
        user_id = decode_token(token)

        # Get IP Address and User-Agent of the request
        ip_address = get_ip_from_request(request)
        user_agent = get_user_agent_from_request(request)

        # Log action
        await log_action(
            action='logout',
            auditable_type='user',
            auditable_id=user_id,
            user_id=user_id,
            old_values=None,
            new_values=None,
            ip_address=ip_address,
            user_agent=user_agent)
    except ValueError:
        pass
    # ==== END OF AUDIT LOGS ENTRY ====
    response.delete_cookie(key="access_token")
    request.session["flash"] = "Successfully logged out."
    request.session["flash_type"] = "info"
    return response
