from io import BytesIO

import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import text

from app.database import engine

# ==========================================
# TICKET DATABASE OPERATIONS
# ==========================================

async def create_ticket(
    order_id: int,
    ticket_type_id: int,
    holder_name: str,
    holder_cpf: str,
    price_paid: int
) -> int:
    """
    Create a new ticket in the database.
    
    Args:
        order_id: Order ID that this ticket belongs to
        ticket_type_id: Ticket type ID
        holder_name: Name of the ticket holder
        holder_cpf: CPF of the ticket holder (format: 000.000.000-00)
        price_paid: Price paid for this ticket in cents
    
    Returns:
        int: The newly created ticket's ID
    
    Raises:
        ValueError: If database operation fails or missing owner fields
    """
    # Check if the ticket has a owner attached to it, if not, raise ValueError
    if not holder_name or not holder_cpf:
        raise ValueError("Ticket must have a owner attached to it.")

    # Connect to database
    async with engine.connect() as conn:
        # INSERT ticket info into the DB
        insert_query = """
        INSERT INTO tickets (order_id, ticket_type_id, holder_name, holder_cpf, price_paid)
        VALUES (:order_id, :ticket_type_id, :holder_name, :holder_cpf, :price_paid)
        """
        await conn.execute(text(insert_query), {"order_id": order_id, "ticket_type_id": ticket_type_id, "holder_name": holder_name, "holder_cpf": holder_cpf, "price_paid": price_paid})
        await conn.commit()

        # Fetch the id of the recently created ticket
        query = await conn.execute(text("SELECT id FROM tickets WHERE id = LAST_INSERT_ID()"))
        ticket_id = query.scalar_one_or_none()

        # Return it
        return ticket_id



async def get_ticket_by_id(ticket_id: int) -> dict | None:
    """
    Fetch a ticket by ID from the database.
    
    Args:
        ticket_id: Ticket ID
    
    Returns:
        dict or None: Ticket data or None if not found
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search for ticket of ID 'ticket_id'
        query = await conn.execute(text("SELECT * FROM tickets WHERE id = :ticket_id"), {"ticket_id": ticket_id})
        ticket_dict = query.mappings().one_or_none() # Convert from row to dict

    # Return ticket dict info or None if empty
    if ticket_dict:
        return dict(ticket_dict)
    
    return None


async def get_tickets_by_order(order_id: int) -> list[dict]:
    """
    Fetch all tickets associated with a specific order.
    
    Args:
        order_id: Order ID
    
    Returns:
        list: List of ticket dicts (empty list if none found)
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for tickets bought in a order of id 'order_id'
        query = await conn.execute(text("SELECT * FROM tickets WHERE order_id = :order_id ORDER BY created_at ASC"), {"order_id": order_id})
        tickets = query.mappings().all()

        # Add all tickets to a list
        ticket_list = [dict(ticket_row) for ticket_row in tickets]

    # Return the ticket list
    return ticket_list

async def get_tickets_by_buyer(buyer_id: int) -> list[dict]:
    """
    Fetch all tickets purchased by a specific buyer (user).
    
    Args:
        buyer_id: User ID of the buyer
    
    Returns:
        list: List of ticket dicts (empty list if none found)
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for tickets under a certain buyer
        search_query = """
        SELECT t.* FROM tickets t
        JOIN orders o ON t.order_id = o.id
        WHERE o.buyer_id = :buyer_id
        ORDER BY t.created_at DESC
        """
        search = await conn.execute(text(search_query), {"buyer_id": buyer_id})
        tickets = search.mappings().all()

        # Add all tickets to a list
        ticket_list = [dict(ticket_row) for ticket_row in tickets]

    # Return ticket list
    return ticket_list


async def update_ticket_holder(
    ticket_id: int,
    holder_name: str,
    holder_cpf: str
) -> bool:
    """
    Update ticket holder information (name and CPF).
    
    Args:
        ticket_id: Ticket ID
        holder_name: New holder name
        holder_cpf: New holder CPF
    
    Returns:
        bool: True if successful
    
    Raises:
        ValueError: If ticket not found or database operation fails
    """
    async with engine.connect() as conn:
        # Check if the ticket exists
        query = await conn.execute(text("SELECT * FROM tickets WHERE id = :ticket_id"), {"ticket_id": ticket_id})
        existing_ticket = query.mappings().one_or_none()

        # If it doesn't exist, raise ValueError
        if not existing_ticket:
            raise ValueError("Ticket not found.")

        # Else, create a dyanmic query that changes the holder's info
        updates = []
        params = {"ticket_id": ticket_id}

        # Update the holder name
        updates.append("holder_name = :holder_name")
        params["holder_name"] = holder_name
        
        # Update the holder CPF
        updates.append("holder_cpf = :holder_cpf")
        params["holder_cpf"] = holder_cpf

        if not updates:
            # If there wan't any updates, just return True for what's current registered
            return True

        # Base query with all fields
        query = f"UPDATE tickets SET {', '.join(updates)} WHERE id = :ticket_id"
        
        # UPDATE new information into the database
        await conn.execute(text(query), params)
        await conn.commit()

    # Return success
    return True

async def update_ticket_status(
    ticket_id: int,
    status: str
) -> bool:
    """
    Update ticket status (valid, used, cancelled).
    
    Args:
        ticket_id: Ticket ID
        status: New status (valid, used, cancelled)
    
    Returns:
        bool: True if successful
    
    Raises:
        ValueError: If ticket not found or database operation fails
    """
    async with engine.connect() as conn:
        # Check if the ticket exists
        query = await conn.execute(text("SELECT * FROM tickets WHERE id = :ticket_id"), {"ticket_id": ticket_id})
        existing_ticket = query.mappings().one_or_none()

        # If it doesn't, return ValueError
        if not existing_ticket:
            raise ValueError("Ticket not found.")

        # Else, Update ticket's status
        await conn.execute(text("UPDATE tickets SET status = :status WHERE id = :ticket_id"), {"status": status, "ticket_id": ticket_id})
        await conn.commit()

    # Return success
    return True

async def mark_ticket_as_used(ticket_id: int) -> bool:
    """
    Mark a ticket as 'used' (for event check-in).
    
    Args:
        ticket_id: Ticket ID
    
    Returns:
        bool: True if successful
    """
    # Mark ticket as 'used'
    result = await update_ticket_status(ticket_id, 'used')

    # Return result
    return result


# ==========================================
# TICKET VALIDATION & BUSINESS LOGIC
# ==========================================

async def check_ticket_ownership(ticket_id: int, buyer_id: int) -> bool:
    """
    Verify that a ticket belongs to a specific buyer.
    
    Args:
        ticket_id: Ticket ID
        buyer_id: User ID of the buyer
    
    Returns:
        bool: True if ticket belongs to buyer, False otherwise
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB to see if the ticket has a certain buyer
        ownership_query = """
        SELECT t.id FROM tickets t
        JOIN orders o ON t.order_id = o.id
        WHERE t.id = :ticket_id AND o.buyer_id = :buyer_id
        """

        query = await conn.execute(text(ownership_query), {"ticket_id": ticket_id, "buyer_id": buyer_id})
        is_owner = query.mappings().one_or_none()

        # If not the same person, return False
        if not is_owner:
            return False

    # Else, return True
    return True


async def get_order_tickets_count(order_id: int) -> int:
    """
    Get the count of tickets for a specific order.
    
    Args:
        order_id: Order ID
    
    Returns:
        int: Number of tickets in this order
    """
    # Connect to database
    async with engine.connect() as conn:
        # Count how many tickets are connected to a certain order
        query = await conn.execute(text("SELECT COUNT(*) as count FROM tickets WHERE order_id = :order_id"), {"order_id": order_id})
        ticket_count = query.scalar()

    # Return ticket count
    return ticket_count

# ==========================================
# TICKET PDF GENERATION
# ==========================================

async def generate_ticket_pdf(ticket_id: int) -> bytes:
    """
    Generate a PDF for a ticket with QR code.
    
    Args:
        ticket_id: Ticket ID
    
    Returns:
        bytes: PDF file content
    
    Raises:
        ValueError: If ticket not found or PDF generation fails
    """
    # Fetch ticket
    ticket = await get_ticket_by_id(ticket_id)

    if not ticket:
        raise ValueError("Ticket not found.")

    try:
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Header
        p.setFont("Helvetica-Bold", 20)
        p.drawString(100, 700, f"TICKET #{ticket_id}")
        
        # Holder data
        p.setFont("Helvetica", 12)
        p.drawString(100, 660, f"Holder Name: {ticket['holder_name']}")
        p.drawString(100, 640, f"CPF: {ticket['holder_cpf']}")
        p.drawString(100, 620, f"Status: {ticket['status']}")
        
        # QR code generation
        qr_data = f"Ticket ID: {ticket['id']} | CPF: {ticket['holder_cpf']} | Status: {ticket['status']}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Conversion and image rendering
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        
        reader = ImageReader(qr_buffer)
        p.drawImage(reader, 100, 450, width=150, height=150)
        
        # Final PDF
        p.showPage()
        p.save()
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
        
    except Exception as e:
        raise ValueError(f"Error during PDF generation: {str(e)}")