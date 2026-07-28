"""
Application entry point.

This file serves as the project's main entry point.
The FastAPI instance is defined in app/main.py.
This file imports and exposes it so that uvicorn can locate it.

To run the application (in debug mode):
    python -m uvicorn main:app --reload
"""
from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)