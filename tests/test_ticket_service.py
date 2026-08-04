from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from validate_docbr import CPF

from app.services.auth_service import create_user
from app.services.event_service import create_event, create_ticket_type
from app.services.order_service import create_order
from app.services.ticket_service import (
    check_ticket_ownership,
    create_ticket,
    generate_ticket_pdf,
    get_order_tickets_count,
    get_ticket_by_id,
    get_tickets_by_buyer,
    get_tickets_by_order,
    mark_ticket_as_used,
    update_ticket_holder,
    update_ticket_status,
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

@pytest.fixture
async def buyer(clean_db):
    """Create a test buyer"""
    unique_id = str(uuid4())[:8]
    
    user_id = await create_user(
        name="Ticket Buyer",
        email=f"buyer-{unique_id}@example.com",
        phone_number=f"+55119{unique_id[:8]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="RJ",
        city="Rio de Janeiro"
    )
    return {"id": user_id}

@pytest.fixture
async def order_with_event(organizer, buyer):
    """Create an order with event for ticket tests"""
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
        price=100,
        quantity_available=50
    )
    
    order_id = await create_order(
        buyer_id=buyer["id"],
        event_id=event_id,
        ticket_type_id=ticket_type_id,
        quantity=3,
        total_amount=30000
    )
    
    return {
        "order_id": order_id,
        "event_id": event_id,
        "ticket_type_id": ticket_type_id,
        "buyer_id": buyer["id"],
        "organizer_id": organizer["id"]
    }

@pytest.mark.asyncio
async def test_create_ticket(order_with_event):
    """Test creating a ticket"""
    ticket_id = await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="John Doe",
        holder_cpf="123.456.789-10",
        price_paid=10000
    )
    
    assert ticket_id is not None
    assert isinstance(ticket_id, int)
    assert ticket_id > 0

@pytest.mark.asyncio
async def test_create_ticket_missing_holder():
    """Test that creating ticket without holder info fails"""
    unique_id = str(uuid4())[:8]
    uid1 = str(uuid4())[:8]
    uid2 = str(uuid4())[:8]
    
    # Create minimal order
    organizer_id = await create_user(
        name="Organizer",
        email=f"org-{unique_id}@example.com",
        phone_number=f"+551197{uid1[:7]}",
        password="Pass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    buyer_id = await create_user(
        name="Buyer",
        email=f"buy-{unique_id}@example.com",
        phone_number=f"+551196{uid2[:7]}",
        password="Pass123!",
        cpf = cpf_gen.generate(mask=True),
        state="RJ",
        city="Rio"
    )
    
    start_date = datetime.now(timezone.utc) + timedelta(days=7)
    end_date = start_date + timedelta(hours=2)
    
    event_id = await create_event(
        organizer_id=organizer_id,
        title="Test",
        description="Test",
        banner_url=None,
        category="entertainment",
        state="SP",
        city="SP",
        address="Rua",
        total_capacity=100,
        start_date=start_date,
        end_date=end_date
    )
    
    ticket_type_id = await create_ticket_type(
        event_id=event_id,
        type="standard",
        price=100,
        quantity_available=50
    )
    
    order_id = await create_order(
        buyer_id=buyer_id,
        event_id=event_id,
        ticket_type_id=ticket_type_id,
        quantity=1,
        total_amount=10000
    )
    
    # Try to create ticket without holder name
    with pytest.raises(ValueError):
        await create_ticket(
            order_id=order_id,
            ticket_type_id=ticket_type_id,
            holder_name="",  # Empty!
            holder_cpf="123.456.789-10",
            price_paid=10000
        )

@pytest.mark.asyncio
async def test_get_ticket_by_id(order_with_event):
    """Test fetching ticket by ID"""
    ticket_id = await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="John Doe",
        holder_cpf="123.456.789-10",
        price_paid=10000
    )
    
    ticket = await get_ticket_by_id(ticket_id)
    
    assert ticket is not None
    assert ticket["id"] == ticket_id
    assert ticket["holder_name"] == "John Doe"
    assert ticket["order_id"] == order_with_event["order_id"]

@pytest.mark.asyncio
async def test_get_ticket_by_id_not_found():
    """Test that non-existent ticket returns None"""
    ticket = await get_ticket_by_id(99999)
    assert ticket is None

@pytest.mark.asyncio
async def test_get_tickets_by_order(order_with_event):
    """Test fetching tickets by order"""
    # Create multiple tickets
    await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="John Doe",
        holder_cpf="123.456.789-10",
        price_paid=10000
    )
    
    await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="Jane Smith",
        holder_cpf="987.654.321-01",
        price_paid=10000
    )
    
    tickets = await get_tickets_by_order(order_with_event["order_id"])
    
    assert len(tickets) >= 2
    assert all(t["order_id"] == order_with_event["order_id"] for t in tickets)

@pytest.mark.asyncio
async def test_get_tickets_by_buyer(order_with_event):
    """Test fetching tickets by buyer"""
    # Create ticket
    await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="John Doe",
        holder_cpf="123.456.789-10",
        price_paid=10000
    )
    
    tickets = await get_tickets_by_buyer(order_with_event["buyer_id"])
    
    assert len(tickets) >= 1
    assert all(t["order_id"] == order_with_event["order_id"] for t in tickets)

@pytest.mark.asyncio
async def test_update_ticket_holder(order_with_event):
    """Test updating ticket holder information"""
    ticket_id = await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="John Doe",
        holder_cpf="123.456.789-10",
        price_paid=10000
    )
    
    # Update holder
    result = await update_ticket_holder(
        ticket_id=ticket_id,
        holder_name="Jane Smith",
        holder_cpf="987.654.321-01"
    )
    
    assert result is True
    
    # Verify update
    ticket = await get_ticket_by_id(ticket_id)
    assert ticket["holder_name"] == "Jane Smith"
    assert ticket["holder_cpf"] == "987.654.321-01"

@pytest.mark.asyncio
async def test_update_ticket_holder_not_found():
    """Test updating non-existent ticket fails"""
    with pytest.raises(ValueError):
        await update_ticket_holder(
            ticket_id=99999,
            holder_name="Jane Smith",
            holder_cpf="987.654.321-01"
        )

@pytest.mark.asyncio
async def test_update_ticket_status(order_with_event):
    """Test updating ticket status"""
    ticket_id = await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="John Doe",
        holder_cpf="123.456.789-10",
        price_paid=10000
    )
    
    # Update status
    result = await update_ticket_status(ticket_id, "used")
    
    assert result is True
    
    # Verify update
    ticket = await get_ticket_by_id(ticket_id)
    assert ticket["status"] == "used"

@pytest.mark.asyncio
async def test_mark_ticket_as_used(order_with_event):
    """Test marking ticket as used"""
    ticket_id = await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="John Doe",
        holder_cpf="123.456.789-10",
        price_paid=10000
    )
    
    # Mark as used
    result = await mark_ticket_as_used(ticket_id)
    
    assert result is True
    
    # Verify
    ticket = await get_ticket_by_id(ticket_id)
    assert ticket["status"] == "used"

@pytest.mark.asyncio
async def test_check_ticket_ownership(order_with_event):
    """Test checking ticket ownership"""
    ticket_id = await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="John Doe",
        holder_cpf="123.456.789-10",
        price_paid=10000
    )
    
    # Check ownership (should be buyer)
    is_owner = await check_ticket_ownership(ticket_id, order_with_event["buyer_id"])
    assert is_owner is True
    
    # Check wrong buyer
    is_owner = await check_ticket_ownership(ticket_id, 99999)
    assert is_owner is False

@pytest.mark.asyncio
async def test_get_order_tickets_count(order_with_event):
    """Test getting ticket count for order"""
    # Create 3 tickets
    for i in range(3):
        await create_ticket(
            order_id=order_with_event["order_id"],
            ticket_type_id=order_with_event["ticket_type_id"],
            holder_name=f"Person {i}",
            holder_cpf=f"111.111.111-{i:02d}",
            price_paid=10000
        )
    
    count = await get_order_tickets_count(order_with_event["order_id"])
    
    assert count == 3

@pytest.mark.asyncio
async def test_generate_ticket_pdf(order_with_event):
    """Test generating ticket PDF"""
    ticket_id = await create_ticket(
        order_id=order_with_event["order_id"],
        ticket_type_id=order_with_event["ticket_type_id"],
        holder_name="John Doe",
        holder_cpf="123.456.789-10",
        price_paid=10000
    )
    
    # Generate PDF
    pdf_bytes = await generate_ticket_pdf(ticket_id)
    
    assert pdf_bytes is not None
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0

@pytest.mark.asyncio
async def test_generate_ticket_pdf_not_found():
    """Test generating PDF for non-existent ticket fails"""
    with pytest.raises(ValueError):
        await generate_ticket_pdf(99999)