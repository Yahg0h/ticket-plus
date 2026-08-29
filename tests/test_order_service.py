from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from validate_docbr import CPF

from app.services.auth_service import create_user
from app.services.event_service import create_event, create_ticket_type
from app.services.order_service import (
    calculate_order_total,
    cancel_order,
    create_order,
    get_order_by_id,
    get_orders_by_buyer,
    update_order_payment_status,
    update_order_status,
    validate_ticket_availability,
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
async def event_with_ticket_type(organizer):
    """Create event with ticket type for orders"""
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
        price=10000,  # 10000 cents = R$ 100
        quantity_available=50
    )
    
    return {
        "event_id": event_id,
        "ticket_type_id": ticket_type_id,
        "price": 10000  # Price in cents
    }

@pytest.mark.asyncio
async def test_create_order(buyer, event_with_ticket_type):
    """Test creating an order"""
    order_id = await create_order(
        buyer_id=buyer["id"],
        event_id=event_with_ticket_type["event_id"],
        ticket_type_id=event_with_ticket_type["ticket_type_id"],
        quantity=2,
        total_amount=20000  # 2 x R$ 100 in cents
    )
    
    assert order_id is not None
    assert isinstance(order_id, int)
    assert order_id > 0

@pytest.mark.asyncio
async def test_get_order_by_id(buyer, event_with_ticket_type):
    """Test fetching order by ID"""
    order_id = await create_order(
        buyer_id=buyer["id"],
        event_id=event_with_ticket_type["event_id"],
        ticket_type_id=event_with_ticket_type["ticket_type_id"],
        quantity=2,
        total_amount=20000
    )
    
    order = await get_order_by_id(order_id)
    
    assert order is not None
    assert order["id"] == order_id
    assert order["buyer_id"] == buyer["id"]
    assert order["quantity"] == 2

@pytest.mark.asyncio
async def test_get_order_by_id_not_found():
    """Test that non-existent order returns None"""
    order = await get_order_by_id(99999)
    assert order is None

@pytest.mark.asyncio
async def test_get_orders_by_buyer(buyer, event_with_ticket_type):
    """Test fetching orders by buyer"""
    # Create multiple orders
    order_id_1 = await create_order(
        buyer_id=buyer["id"],
        event_id=event_with_ticket_type["event_id"],
        ticket_type_id=event_with_ticket_type["ticket_type_id"],
        quantity=1,
        total_amount=10000
    )
    
    order_id_2 = await create_order(
        buyer_id=buyer["id"],
        event_id=event_with_ticket_type["event_id"],
        ticket_type_id=event_with_ticket_type["ticket_type_id"],
        quantity=2,
        total_amount=20000
    )
    
    # Fetch orders
    orders = await get_orders_by_buyer(buyer["id"])
    
    assert len(orders) >= 2
    assert any(o["id"] == order_id_1 for o in orders)
    assert any(o["id"] == order_id_2 for o in orders)

@pytest.mark.asyncio
async def test_update_order_payment_status(buyer, event_with_ticket_type):
    """Test updating order payment status"""
    order_id = await create_order(
        buyer_id=buyer["id"],
        event_id=event_with_ticket_type["event_id"],
        ticket_type_id=event_with_ticket_type["ticket_type_id"],
        quantity=2,
        total_amount=20000
    )
    
    # Update payment status
    result = await update_order_payment_status(order_id, "paid", "stripe_payment_123")
    
    assert result is True
    
    # Verify update
    order = await get_order_by_id(order_id)
    assert order["payment_status"] == "paid"
    assert order["stripe_payment_id"] == "stripe_payment_123"

@pytest.mark.asyncio
async def test_update_order_status(buyer, event_with_ticket_type):
    """Test updating order status"""
    order_id = await create_order(
        buyer_id=buyer["id"],
        event_id=event_with_ticket_type["event_id"],
        ticket_type_id=event_with_ticket_type["ticket_type_id"],
        quantity=2,
        total_amount=20000
    )
    
    # Update order status
    result = await update_order_status(order_id, "confirmed")
    
    assert result is True
    
    # Verify update
    order = await get_order_by_id(order_id)
    assert order["order_status"] == "confirmed"

@pytest.mark.asyncio
async def test_cancel_order(buyer, event_with_ticket_type):
    """Test cancelling an order"""
    order_id = await create_order(
        buyer_id=buyer["id"],
        event_id=event_with_ticket_type["event_id"],
        ticket_type_id=event_with_ticket_type["ticket_type_id"],
        quantity=2,
        total_amount=20000
    )
    
    # Cancel order
    result = await cancel_order(order_id)
    
    assert result is True
    
    # Verify cancellation
    order = await get_order_by_id(order_id)
    assert order["order_status"] == "cancelled"

@pytest.mark.asyncio
async def test_validate_ticket_availability(event_with_ticket_type):
    """Test ticket availability validation"""
    # Should have 50 tickets available
    available = await validate_ticket_availability(
        event_with_ticket_type["ticket_type_id"],
        10
    )
    
    assert available is True
    
    # Try to buy more than available
    available = await validate_ticket_availability(
        event_with_ticket_type["ticket_type_id"],
        100  # More than 50
    )
    
    assert available is False

@pytest.mark.asyncio
async def test_calculate_order_total(event_with_ticket_type):
    """Test calculating order total"""
    # Price is 100 (e.g, R$ 100), converted to 10000 cents
    total = await calculate_order_total(
        event_with_ticket_type["ticket_type_id"],
        2  # 2 tickets
    )
    
    # Should be 2 * 10000 = 20000
    assert total == 20000
    
    # Test with different quantity
    total = await calculate_order_total(
        event_with_ticket_type["ticket_type_id"],
        5  # 5 tickets
    )
    
    assert total == 50000

@pytest.mark.asyncio
async def test_calculate_order_total_not_found():
    """Test calculating total for non-existent ticket type"""
    total = await calculate_order_total(99999, 2)
    
    # Should return None if not found
    assert total is None