from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings, templates

# Configure application
app = FastAPI(
    title="TicketPlus",
    description="E-commerce for creating events and buying tickets for events",
    version="1.0.0",
    debug=settings.DEBUG
)

# Configure Jinja2 and flash messages
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET)

# Mount and point to the static directory (CSS, JS and images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Custom handler that fetches every HTTPException and renders a error message to the user
# Errors 404, 500 and 403 renders error.html, while the rest displays a flash message.
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
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

# Root Route (TO BE HERE)