"""
Database async connection configuration for TicketPlus + Database status check.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Creates the DATABASE URL using the credentials from config.py
DATABASE_URL = f"mysql+aiomysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Creates the async engine for MySQL
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

# Creates async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency function for FastAPI
async def get_db():
    """
    FastAPI dependency that provides an asynchronous database session.
    Currently not in use, but ready to be if necessary.

    Yields:
        AsyncSession: An active SQLAlchemy async database session.

    Note:
        Ensures the session is properly closed after request execution,
        even if exceptions occur.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Database connection function
async def check_database_connection() -> tuple[bool, str | None]:
    """
    Check if database is connected by running a simple query.

    Returns:
        tuple: (is_connected: bool, error_message: str | None)
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        return False, str(e)