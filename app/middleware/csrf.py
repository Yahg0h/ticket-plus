"""
CSRF Protection - dependency version.
Validate token only on routes that need it, without breaking multipart.
"""
 
import secrets
from typing import Annotated

from fastapi import Depends, Form, HTTPException, Request


async def validate_csrf(
    request: Request,
    csrf_token: Annotated[str, Form()] = ""
) -> None:
    """
    Dependency to validate CSRF token.
    Use in POST/PUT/DELETE routes that receive forms.

    Example:
        @router.post("/create")
        async def create(request: Request, _=Depends(validate_csrf)):
        ...
    """
    # Generate token if it doesn't exist
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = secrets.token_urlsafe(32)
        request.session.modified = True
    
    expected_token = request.session.get("csrf_token")
    
    if not csrf_token or csrf_token != expected_token:
        raise HTTPException(status_code=403, detail="CSRF token validation failed")
 
 
async def ensure_csrf_token(request: Request) -> None:
    """
    Dependency to ensure the CSRF token exists in the session.
    Use on GET routes that serve forms.
    
    Example:
        @router.get("/create")
        async def get_create(request: Request, _=Depends(ensure_csrf_token)):
            return templates.TemplateResponse(...)
    """
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = secrets.token_urlsafe(32)
        request.session.modified = True