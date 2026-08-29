from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from validate_docbr import CPF

from app.services.auth_service import create_user
from app.services.event_service import (
    create_event,
    create_ticket_type,
    delete_event,
    get_all_events,
    get_event_by_id,
    get_events_by_organizer,
    get_ticket_type_by_id,
    update_event,
)

cpf_gen = CPF()

@pytest.fixture
async def organizer(clean_db):
    """Create a test organizer"""
    unique_id = str(uuid4())[:8]
    
    user_id = await create_user(
        name="Event Organizer",
        email=f"organizer-{unique_id}@example.com",
        phone_number=f"+55119{unique_id[:8]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    return {"id": user_id}

@pytest.mark.asyncio
async def test_create_event_success(organizer):
    """Test successful event creation"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    event_id = await create_event(
        organizer_id=organizer["id"],
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
    
    assert event_id is not None
    assert isinstance(event_id, int)
    assert event_id > 0

@pytest.mark.asyncio
async def test_create_event_past_date(organizer):
    """Test that past event creation fails"""
    start_date = datetime.now(timezone.utc) - timedelta(days=1)
    end_date = start_date + timedelta(hours=2)
    
    with pytest.raises(ValueError) as exc_info:
        await create_event(
            organizer_id=organizer["id"],
            title="Past Concert",
            description="A past concert",
            banner_url=None,
            category="entertainment",
            state="SP",
            city="São Paulo",
            address="Rua Teste, 123",
            total_capacity=100,
            start_date=start_date,
            end_date=end_date
        )
    
    assert "passou" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_create_event_end_before_start(organizer):
    """Test that end date before start date fails"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date - timedelta(hours=1)
    
    with pytest.raises(ValueError) as exc_info:
        await create_event(
            organizer_id=organizer["id"],
            title="Invalid Concert",
            description="Invalid concert",
            banner_url=None,
            category="entertainment",
            state="SP",
            city="São Paulo",
            address="Rua Teste, 123",
            total_capacity=100,
            start_date=start_date,
            end_date=end_date
        )
    
    assert "término" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_get_event_by_id(organizer):
    """Test fetching event by ID"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    event_id = await create_event(
        organizer_id=organizer["id"],
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
    
    event = await get_event_by_id(event_id)
    
    assert event is not None
    assert event["id"] == event_id
    assert event["title"] == "Test Concert"
    assert event["organizer_id"] == organizer["id"]

@pytest.mark.asyncio
async def test_get_event_by_id_not_found():
    """Test that non-existent event returns None"""
    event = await get_event_by_id(99999)
    assert event is None

@pytest.mark.asyncio
async def test_get_events_by_organizer(organizer):
    """Test fetching events by organizer"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    # Create multiple events
    event_id_1 = await create_event(
        organizer_id=organizer["id"],
        title="Event 1",
        description="First event",
        banner_url=None,
        category="entertainment",
        state="SP",
        city="São Paulo",
        address="Rua Teste, 123",
        total_capacity=500,
        start_date=start_date,
        end_date=end_date
    )
    
    event_id_2 = await create_event(
        organizer_id=organizer["id"],
        title="Event 2",
        description="Second event",
        banner_url=None,
        category="corporate",
        state="RJ",
        city="Rio de Janeiro",
        address="Avenida Teste, 456",
        total_capacity=300,
        start_date=start_date + timedelta(days=1),
        end_date=end_date + timedelta(days=1)
    )
    
    # Fetch events
    events = await get_events_by_organizer(organizer["id"])
    
    assert len(events) >= 2
    assert any(e["id"] == event_id_1 for e in events)
    assert any(e["id"] == event_id_2 for e in events)

@pytest.mark.asyncio
async def test_get_all_events(organizer):
    """Test fetching all events with pagination"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    # Create event
    await create_event(
        organizer_id=organizer["id"],
        title="Test Concert",
        description="A test concert",
        banner_url=None,
        category="entertainment",
        state="SP",
        city="São Paulo",
        address="Rua Teste, 123",
        total_capacity=500,
        start_date=start_date,
        end_date=end_date
    )
    
    # Fetch all events (page 1)
    events, total_pages = await get_all_events()
    
    assert len(events) >= 1
    assert total_pages >= 1

@pytest.mark.asyncio
async def test_update_event(organizer):
    """Test updating event"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    event_id = await create_event(
        organizer_id=organizer["id"],
        title="Test Concert",
        description="A test concert",
        banner_url=None,
        category="entertainment",
        state="SP",
        city="São Paulo",
        address="Rua Teste, 123",
        total_capacity=500,
        start_date=start_date,
        end_date=end_date
    )
    
    # Update event
    result = await update_event(
        event_id=event_id,
        organizer_id=organizer["id"],
        title="Updated Concert",
        description="Updated description"
    )
    
    assert result is True
    
    # Verify update
    event = await get_event_by_id(event_id)
    assert event["title"] == "Updated Concert"

@pytest.mark.asyncio
async def test_update_event_unauthorized():
    """Test that unauthorized update raises error"""
    unique_id = str(uuid4())[:8]
    uid1 = str(uuid4())[:8]
    uid2 = str(uuid4())[:8]
    
    # Create another organizer
    other_organizer_id = await create_user(
        name="Other Organizer",
        email=f"other-{unique_id}@example.com",
        phone_number=f"+551199{uid1[:7]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="RJ",
        city="Rio de Janeiro"
    )
    
    # Create first organizer
    unique_id_2 = str(uuid4())[:8]
    first_organizer_id = await create_user(
        name="First Organizer",
        email=f"first-{unique_id_2}@example.com",
        phone_number=f"+551198{uid2[:7]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    # Create event as first organizer
    event_id = await create_event(
        organizer_id=first_organizer_id,
        title="Test Concert",
        description="A test concert",
        banner_url=None,
        category="entertainment",
        state="SP",
        city="São Paulo",
        address="Rua Teste, 123",
        total_capacity=500,
        start_date=start_date,
        end_date=end_date
    )
    
    # Try to update as other organizer
    with pytest.raises(ValueError):
        await update_event(
            event_id=event_id,
            organizer_id=other_organizer_id,
            title="Hacked Event"
        )

@pytest.mark.asyncio
async def test_delete_event(organizer):
    """Test deleting event"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    event_id = await create_event(
        organizer_id=organizer["id"],
        title="Test Concert",
        description="A test concert",
        banner_url=None,
        category="entertainment",
        state="SP",
        city="São Paulo",
        address="Rua Teste, 123",
        total_capacity=500,
        start_date=start_date,
        end_date=end_date
    )
    
    # Delete event
    result = await delete_event(event_id, organizer["id"])
    
    assert result is True
    
    # Verify deletion
    event = await get_event_by_id(event_id)
    assert event is None

@pytest.mark.asyncio
async def test_create_ticket_type(organizer):
    """Test creating ticket type"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    event_id = await create_event(
        organizer_id=organizer["id"],
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
    
    ticket_type_id = await create_ticket_type(
        event_id=event_id,
        type="standard",
        price=10000,
        quantity_available=50
    )
    
    assert ticket_type_id is not None
    assert isinstance(ticket_type_id, int)

@pytest.mark.asyncio
async def test_get_ticket_type_by_id(organizer):
    """Test fetching ticket type by ID"""
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    event_id = await create_event(
        organizer_id=organizer["id"],
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
    
    ticket_type_id = await create_ticket_type(
        event_id=event_id,
        type="standard",
        price=10000,
        quantity_available=50
    )
    
    ticket_type = await get_ticket_type_by_id(ticket_type_id)
    
    assert ticket_type is not None
    assert ticket_type["id"] == ticket_type_id
    assert ticket_type["event_id"] == event_id
    assert ticket_type["type"] == "standard"