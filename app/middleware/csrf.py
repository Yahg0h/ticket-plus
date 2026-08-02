import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CsrfMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware.
    Generates tokens for GET requests and validates on POST/PUT/DELETE.
    """
    
    CSRF_TOKEN_LENGTH = 32
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    
    async def dispatch(self, request: Request, call_next):
        # If it is a safe method (GET, HEAD, OPTIONS)
        if request.method in self.SAFE_METHODS:
            # Generate CSRF token if it doesn't exist in session
            if "csrf_token" not in request.session:
                request.session["csrf_token"] = secrets.token_urlsafe(self.CSRF_TOKEN_LENGTH)
                request.session.modified = True
            return await call_next(request)
        
        # If it is POST/PUT/DELETE, validate CSRF token
        if request.method in {"POST", "PUT", "DELETE"}:
            token_from_form = None
            token_from_header = request.headers.get("x-csrf-token")
            
            content_type = request.headers.get("content-type", "")
            
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                try:
                    body = await request.body()
                    
                    if "application/x-www-form-urlencoded" in content_type:
                        params = body.decode().split("&")
                        for param in params:
                            if "=" in param:
                                key, value = param.split("=", 1)
                                if key == "csrf_token":
                                    from urllib.parse import unquote_plus
                                    token_from_form = unquote_plus(value)
                                    break
                except Exception as e:
                    print(f"Error when parse form: {e}")
            
            # Validate token
            expected_token = request.session.get("csrf_token")
            received_token = token_from_form or token_from_header
            
            print(f"Expected: {expected_token}")
            print(f"Received: {received_token}")
            
            if not received_token or received_token != expected_token:
                return Response(
                    content="CSRF token validation failed",
                    status_code=403
                )
        
        return await call_next(request)