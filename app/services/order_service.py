import uuid

from sqlalchemy import text

from app.database import engine

# ==========================================
# ORDER DATABASE OPERATIONS
# ==========================================

async def create_order(
    buyer_id: int,
    event_id: int,
    ticket_type_id: int,
    quantity: int,
    total_amount: int,
    idempotency_key: str | None = None
) -> int:
    """
    Create a new order in the database with status 'pending'.
    
    Args:
        buyer_id: User ID of the buyer
        event_id: Event ID
        ticket_type_id: Ticket type ID
        quantity: Number of tickets
        total_amount: Total price in cents
        idempotency_key: Unique key to prevent duplicate orders (optional)
    
    Returns:
        int: The newly created order's ID
    
    Raises:
        ValueError: If database operation fails
    """
    # Check if a idempotency key was provided, if not, generate one to stop duplicate requests
    if idempotency_key is None:
        idempotency_key = uuid.uuid4().hex

    # Connect to database
    async with engine.connect() as conn:
        # INSERT into the database
        await conn.execute(text(
            "INSERT INTO orders (buyer_id, event_id, ticket_type_id, quantity, total_amount, idempotency_key) "
            "VALUES (:buyer_id, :event_id, :ticket_type_id, :quantity, :total_amount, :idempotency_key)"
        ), {
            "buyer_id": buyer_id,
            "event_id": event_id,
            "ticket_type_id": ticket_type_id,
            "quantity": quantity,
            "total_amount": total_amount,
            "idempotency_key": idempotency_key
        })
        await conn.commit()

        # Fetch the id of the recently added order
        query = await conn.execute(text("SELECT id FROM orders WHERE id = LAST_INSERT_ID()"))
        order_id = query.scalar() # Convert to int

        # Return id
        return order_id


async def get_order_by_id(order_id: int) -> dict | None:
    """
    Fetch an order by ID from the database.
    
    Args:
        order_id: Order ID
    
    Returns:
        dict or None: Order data or None if not found
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for the order by its id
        query = await conn.execute(text("SELECT * FROM orders WHERE id = :order_id"), {"order_id": order_id})
        order_dict = query.mappings().one_or_none() # Convert from row to dict

        # Return order info dict
        return order_dict


async def get_orders_by_buyer(buyer_id: int) -> list[dict]:
    """
    Fetch all orders created by a specific buyer.
    
    Args:
        buyer_id: User ID of buyer
    
    Returns:
        list: List of order dicts
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for all orders under buyer of id 'buyer_id'
        query = await conn.execute(text("SELECT * FROM orders WHERE buyer_id = :buyer_id ORDER BY created_at DESC"), {"buyer_id": buyer_id})
        orders = query.mappings().all()

        # Add each order to a list
        order_list = [dict(order_row) for order_row in orders]

        # Return order list
        return order_list

async def update_order_payment_status(
    order_id: int,
    payment_status: str,
    stripe_payment_id: str | None = None
) -> bool:
    """
    Update order payment status (after Stripe webhook).
    
    Args:
        order_id: Order ID
        payment_status: New payment status (paid, failed, refunded)
        stripe_payment_id: Stripe payment intent ID (optional)
    
    Returns:
        bool: True if successful
    """
    async with engine.connect() as conn:
        # Create a dyanmic query that changes based on the updates
        updates = []
        params = {"order_id": order_id}

        if payment_status:
            updates.append("payment_status = :payment_status")
            params["payment_status"] = payment_status
        if stripe_payment_id:
            updates.append("stripe_payment_id = :stripe_payment_id")
            params["stripe_payment_id"] = stripe_payment_id

        if not updates:
            # If there wan't any updates, just return True for what's current registered
            return True
        
        # Base query with all selected updates
        query = f"UPDATE orders SET {', '.join(updates)} WHERE id = :order_id"
        
        # UPDATE new information into the database
        await conn.execute(text(query), params)
        await conn.commit()

    # Return success
    return True 


async def update_order_status(
    order_id: int,
    order_status: str,
    completed_at: str | None = None
) -> bool:
    """
    Update order status.
    
    Args:
        order_id: Order ID
        order_status: New order status (confirmed, cancelled, completed)
        completed_at: Completion timestamp (optional)
    
    Returns:
        bool: True if successful
    """
    async with engine.connect() as conn:
        # Create dyanmic query that changes based on updates
        updates = []
        params = {"order_id": order_id}

        if order_status:
            updates.append("order_status = :order_status")
            params["order_status"] = order_status
        if completed_at:
            updates.append("completed_at = :completed_at")
            params["completed_at"] = completed_at
        
        if not updates:
            # If there wan't any updates, just return True for what's current registered
            return True

        # Base query with all selected updates
        query = f"UPDATE orders SET {', '.join(updates)} WHERE id = :order_id"
        
        # UPDATE new information into the database
        await conn.execute(text(query), params)
        await conn.commit()

    # Return True if successful
    return True

async def cancel_order(order_id: int) -> bool:
    """
    Cancel an order (set status to 'cancelled').
    
    Args:
        order_id: Order ID
    
    Returns:
        bool: True if successful
    """
    # Cancel the order
    is_cancelled = await update_order_status(order_id, 'cancelled')

    # Return if successful (True) or not (False)
    return is_cancelled


# ==========================================
# ORDER VALIDATION & BUSINESS LOGIC
# ==========================================

async def validate_ticket_availability(ticket_type_id: int, quantity: int) -> bool:
    """
    Check if enough tickets are available for purchase.
    
    Args:
        ticket_type_id: Ticket type ID
        quantity: Number of tickets to purchase
    
    Returns:
        bool: True if available, False otherwise
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for the quantity of tickets available and already sold
        query = await conn.execute(text("SELECT quantity_available, quantity_sold FROM ticket_types WHERE id = :ticket_type_id"), {"ticket_type_id": ticket_type_id})
        results = query.mappings().one_or_none()

        # Check the available tickets for sale
        available = results["quantity_available"] - results["quantity_sold"]

        # If the available ticket quantity allows the purchase of 'quantity' of tickets, return True; else, return False
        return available >= quantity


async def get_ticket_type_with_event(ticket_type_id: int) -> dict | None:
    """
    Fetch ticket type with related event information.
    
    Args:
        ticket_type_id: Ticket type ID
    
    Returns:
        dict or None: Ticket type with event info or None if not found
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for the event + its ticket type info togheter
        tt_event_query = """
        SELECT tt.*, e.organizer_id, e.start_date FROM ticket_types tt
        JOIN events e ON tt.event_id = e.id
        WHERE tt.id = :ticket_type_id
        """
        search = await conn.execute(text(tt_event_query), {"ticket_type_id": ticket_type_id})
        tt_event_info = search.mappings().one_or_none()

        # Return all info in a dict (or None)
        return tt_event_info


# ==========================================
# PAYMENT PROCESSING (Stripe Webhook)
# ==========================================

async def process_successful_payment(order_id: int, stripe_payment_id: str) -> bool:
    """
    Process a successful payment from Stripe webhook.
    
    Args:
        order_id: Order ID
        stripe_payment_id: Stripe payment intent ID
    
    Returns:
        bool: True if successful
    
    Note: This function is called from the Stripe webhook handler in routes/orders.py
    """
    # Fetch the order information
    order = await get_order_by_id(order_id)

    # Update payment_status to paid
    await update_order_payment_status(order_id, 'paid', stripe_payment_id)

    # Update order_status to confirmed
    await update_order_status(order_id, 'confirmed')

    # Connect to database
    async with engine.connect() as conn:
        # Update quantity_sold in ticket_types
        qty_query = """
        UPDATE ticket_types tt
        JOIN (
            SELECT ticket_type_id, COUNT(*) as qty
            FROM tickets
            WHERE order_id = :order_id
            GROUP BY ticket_type_id
            ) t_count ON tt.id = t_count.ticket_type_id
            SET tt.quantity_sold = tt.quantity_sold + t_count.qty
        """
        await conn.execute(text(qty_query), {"order_id": order_id})
        await conn.commit()

        # Update available_tickets in events
        event_query = """
        UPDATE events
        SET available_tickets = available_tickets - (
            SELECT COUNT(*) FROM tickets WHERE order_id = :order_id
        )
        WHERE id = :event_id
        """
        await conn.execute(text(event_query), {"order_id": order_id, "event_id": order["event_id"]})
        await conn.commit()

        # Return True
        return True    


async def calculate_order_total(ticket_type_id: int, quantity: int) -> int | None:
    """
    Calculate total order amount based on ticket type price and quantity.
    
    Args:
        ticket_type_id: Ticket type ID
        quantity: Number of tickets
    
    Returns:
        int or None: Total amount in cents, or None if ticket type not found
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for the price of a ticket-type
        query = await conn.execute(text("SELECT price FROM ticket_types WHERE id = :ticket_type_id"), {"ticket_type_id": ticket_type_id})
        price = query.scalar_one_or_none() # Convert from row to int

        # Calculate the total order amount
        total = price * quantity

        # Return the total amount
        return total