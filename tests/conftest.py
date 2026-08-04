import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import text
from validate_docbr import CPF

# Adds the root directory to PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine
from app.services.auth_service import create_user
from app.services.event_service import create_event, create_ticket_type

cpf_generator = CPF()


# Mock external services (.send)
@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    mock_service = MagicMock()
    mock_service.send = MagicMock(return_value=True)
    
    targets = [
        "app.services.auth_service",
        "app.services.event_service",
        "app.services.order_service",
        "app.services.ticket_service",
        "app.services.user_service",
    ]
    service_attrs = ["email_service", "notification_service", "mail_service", "audit_service", "ws_manager"]
    
    for target in targets:
        for attr in service_attrs:
            monkeypatch.setattr(f"{target}.{attr}", mock_service, raising=False)


# Clear the connection pool after each test (Eliminates the 'attached to a different loop' error)
@pytest.fixture(autouse=True)
async def reset_db_engine():
    yield
    await engine.dispose()


# Truncate tables
@pytest.fixture
async def clean_db():
    tables = ['audit_logs', 'tickets', 'orders', 'ticket_types', 'events', 'users']
    
    async with engine.begin() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        for table in tables:
            await conn.execute(text(f"TRUNCATE TABLE {table}"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        
    yield
    
    async with engine.begin() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        for table in tables:
            await conn.execute(text(f"TRUNCATE TABLE {table}"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

# ==========================================
# GLOBAL MOCKS (Fixes AttributeError: 'NoneType' object has no attribute 'send')
# ==========================================
# conftest.py
@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """Ensures that any email/notification sending service is a functional mock."""
    mock_service = MagicMock()
    mock_service.send = MagicMock(return_value=True)
    
    # Modules that attempt to access email/notification/WebSocket services
    targets = [
        "app.services.auth_service",
        "app.services.event_service",
        "app.services.order_service",
        "app.services.ticket_service",
        "app.services.user_service",
    ]
    
    # Common attributes that typically call .send()
    service_attrs = [
        "email_service",
        "notification_service",
        "mail_service",
        "audit_service",
        "ws_manager",
    ]
    
    for target in targets:
        for attr in service_attrs:
            # Forces the attribute to be our mock_service instead of None
            monkeypatch.setattr(f"{target}.{attr}", mock_service, raising=False)


# ==========================================
# ENVIRONMENT SETUP FIXTURES
# ==========================================
@pytest.fixture(scope="session")
def event_loop():
    """Event loop for asynchronous tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def clean_db():
    """Cleans the database before and after each test."""
    tables = [
        'audit_logs', 'tickets', 'orders', 'ticket_types', 
        'events', 'users'
    ]
    
    try:
        async with engine.begin() as conn:
            # Temporarily disables foreign keys in MySQL to avoid constraint errors.
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            for table in tables:
                await conn.execute(text(f"TRUNCATE TABLE {table}"))
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    except Exception as e:
        print(f"Warning: Could not truncate tables: {e}")
    
    yield
    
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            for table in tables:
                await conn.execute(text(f"TRUNCATE TABLE {table}"))
            await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
    except Exception:
        pass


# ==========================================
# DATA FIXTURES FOR THE TESTS
# ==========================================
@pytest.fixture
async def test_user(clean_db):
    """Creates a standard user with a valid CPF (14 characters) and a clean phone number."""
    unique_id = str(uuid4())[:8]
    email = f"test-{unique_id}@example.com"
    phone = f"+55119{unique_id[:8]}"
    cpf = cpf_generator.generate(mask=True)  # Ex: 123.456.789-10 (14 chars)

    user_id = await create_user(
        name="Test User",
        email=email,
        phone_number=phone,
        password="TestPassword123!",
        cpf=cpf,
        state="SP",
        city="São Paulo"
    )
    
    return {
        "id": user_id,
        "name": "Test User",
        "email": email,
        "phone_number": phone,
        "cpf": cpf,
        "state": "SP",
        "city": "São Paulo"
    }


@pytest.fixture
async def test_organizer(clean_db):
    """Creates a test organizer"""
    unique_id = str(uuid4())[:8]
    email = f"organizer-{unique_id}@example.com"
    phone = f"+55119{unique_id[:8]}"
    cpf = cpf_generator.generate(mask=True)

    user_id = await create_user(
        name="Event Organizer",
        email=email,
        phone_number=phone,
        password="SecurePass123!",
        cpf=cpf,
        state="SP",
        city="São Paulo"
    )
    
    return {"id": user_id, "email": email, "cpf": cpf}


@pytest.fixture
async def test_event(test_organizer):
    """Creates a test event"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    event_id = await create_event(
        organizer_id=test_organizer["id"],
        title="Test Concert",
        description="A test concert",
        banner_url=None,
        category="entertainment",
        state="SP",
        city="São Paulo",
        address="Rua Teste, 123",
        total_capacity=100,
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "id": event_id,
        "organizer_id": test_organizer["id"],
        "title": "Test Concert",
        "total_capacity": 100,
        "start_date": start_date,
        "end_date": end_date
    }


@pytest.fixture
async def test_ticket_type(test_event):
    """Creates a test ticket type"""
    if not test_event:
        return None
    
    ticket_type_id = await create_ticket_type(
        event_id=test_event["id"],
        type="standard",
        price=10000,  # $ or R$ 100 in cents
        quantity_available=50
    )
    
    return {
        "id": ticket_type_id,
        "event_id": test_event["id"],
        "type": "standard",
        "price": 10000,
        "quantity_available": 50
    }