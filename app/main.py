"""
The heart of the application.
It manages the application configuration and the addition of features such as rate limiters, middleware, exception handlers, 
static file serving, and routes (root, health check, CSRF token, about), as well as the integration of all route handlers from `app/routes`.
"""

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings, templates
from app.database import check_database_connection
from app.middleware.rate_limiter import limiter
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.events import router as events_router
from app.routes.orders import router as orders_router
from app.routes.tickets import router as tickets_router
from app.routes.users import router as users_router
from app.services.auth_service import get_current_user_optional

# Configure application
app = FastAPI(
    title="TicketPlus",
    description="E-commerce for creating events and buying tickets for events",
    version="1.0.0",
    debug=settings.DEBUG
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middlewares (Jinja2 and Flash messages)
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET)

# Mount and point to the static directory (CSS, JS and images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTPException errors.
    Errors 404, 500 and 403 renders error.html, while the rest displays a flash message.
    """
    # If the error is (404, 500, 403), then render error.html
    if exc.status_code in [404, 500, 403]:
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "request": request,
                "status_code": exc.status_code,
                "detail": exc.detail
            },
            status_code=exc.status_code
        )
    
    # Else for other errors (401, 409, etc), store in a flash message and redirect
    response = RedirectResponse(url="/", status_code=303)
    request.session["flash"] = exc.detail
    request.session["flash_type"] = "error"  # Message type (error, success, info)
    return response

@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Handle rate limit exceeded errors (HTTP 429).
    Show specific limit message and wait time.
    """
    # Extract message info
    detail = exc.detail  # E.g: "5 per 15 minutes"
    
    # Detail parsing (ex: "5 per 15 minutes" -> limit and wait time)
    parts = detail.split(" per ")
    if len(parts) == 2:
        limit_count = parts[0]  # "5"
        time_period = parts[1]  # "15 minutes"
        message = f"Limite de {limit_count} requisições por {time_period} excedido. Por favor, aguarde alguns minutos antes de tentar novamente."
    else:
        message = "Too Many Requests. Tente novamente em alguns minutos."
    
    response = RedirectResponse(url="/", status_code=303)
    request.session["flash"] = message
    request.session["flash_type"] = "warning"
    return response

@app.exception_handler(RequestValidationError)
async def custom_validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors (422) sending flash messages
    and redirecting back to the previous page.
    """
    # Gets the URL from where the user came from or goes to fallback "/"
    referer = request.headers.get("referer", "/")
    
    # Flash message
    request.session["flash"] = "Invalid form data. Please check your inputs."
    request.session["flash_type"] = "danger"
    
    # Redirect
    return RedirectResponse(url=referer, status_code=303)

# Root route
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user_id: int | None = Depends(get_current_user_optional)):
    """
    Render the home page or redirect to login.

    Checks if the user is authenticated. If authenticated, renders the main dashboard/index 
    template; otherwise, redirects the user to the login page.
    """
    # If the user isn't logged in (after token verification with dependency), redirect to /login
    if user_id is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    # Else, if the user is logged in, render index.html
    return templates.TemplateResponse(
        request,
        "index.html",
        {"request": request, "user_id": user_id}
    )

# Database health check route
@app.get("/health", response_class=HTMLResponse)
async def health_check(request: Request, user_id: int | None = Depends(get_current_user_optional)):
    """
    Health check endpoint showing service and database status.
    """
    connect_check, error_message = await check_database_connection()
    now = datetime.now(tz=timezone.utc)
    health_dict = {
        "service_name": 'TicketPlus',
        "service_version": '1.0.0',
        "db_connected": connect_check,
        "checked_at": now,
        "db_error": error_message
    }

    # Render health status page with everything
    return templates.TemplateResponse(
        request,
        "health.html",
        {
            "request": request,
            "service_name": health_dict["service_name"],
            "service_version": health_dict["service_version"],
            "db_connected": health_dict["db_connected"],
            "checked_at": health_dict["checked_at"],
            "db_error": health_dict["db_error"]
        }
    )

# CSRF token route
@app.get("/csrf-token")
async def get_csrf_token(request: Request):
    """
    Endpoint to get the CSRF token to forms.
    """
    return {"csrf_token": request.session.get("csrf_token", "")}

# About route
@app.get("/about", response_class=HTMLResponse)
async def about(request: Request, user_id: int | None = Depends(get_current_user_optional)):
    """
    Render About page with project information.
    """
    return templates.TemplateResponse(
        request,
        "about.html",
        {
            "request": request,
            "user_id": user_id
        }
    )

# Auth router
app.include_router(auth_router)

# Users router
app.include_router(users_router)

# Events router
app.include_router(events_router)

# Orders (checkout) router
app.include_router(orders_router)

# Tickets router
app.include_router(tickets_router)

# Admin router
app.include_router(admin_router)