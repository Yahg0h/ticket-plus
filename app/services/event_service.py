"""
All services related to event management used across all TicketPlus routes.
"""

from datetime import datetime, timezone

from sqlalchemy import text

from app.database import engine

# ==========================================
# EVENT DATABASE OPERATIONS
# ==========================================

async def create_event(
    organizer_id: int,
    title: str,
    description: str | None,
    banner_url: str | None,
    category: str,
    state: str,
    city: str,
    address: str,
    total_capacity: int,
    start_date: str,
    end_date: str
) -> int:
    """
    Create a new event in the database.
    
    Args:
        organizer_id: User ID of the event creator
        title: Event title
        description: Event description (optional)
        banner_url: URL to event banner image (optional)
        category: Event category (enum)
        state: Event state
        city: Event city
        address: Event address
        total_capacity: Total event capacity
        start_date: Event start date (YYYY-MM-DD HH:MM:SS)
        end_date: Event end date (YYYY-MM-DD HH:MM:SS)
    
    Returns:
        int: The newly created event's ID
    
    Raises:
        ValueError: If something goes wrong with database operation
    """
    # Check if the start date is from a day before today
    now = datetime.now(timezone.utc)

    # Convert start_date and end_date to aware if they're datetime objects
    if isinstance(start_date, datetime) and not start_date.tzinfo:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if isinstance(end_date, datetime) and not end_date.tzinfo:
        end_date = end_date.replace(tzinfo=timezone.utc)

    if start_date < now:
        raise ValueError("Não é possível definir a data de início de um evento para um dia que já passou.")
    
    # Check if the event end_date is early than the start_date, if it is, return ValueError
    if end_date < start_date:
        raise ValueError("A data de término do evento não pode ser anterior à data de início.")
    
    # Connect to database
    async with engine.connect() as conn:
        # INSERT event information into the database
        event_query = """
        INSERT INTO events (organizer_id, title, description, banner_url, category, state, city, address, total_capacity, available_tickets, start_date, end_date) 
        VALUES (:organizer_id, :title, :description, :banner_url, :category, :state, :city, :address, :total_capacity, :available_tickets, :start_date, :end_date)
        """
        await conn.execute(text(event_query), {"organizer_id": organizer_id, "title": title, "description": description, "banner_url": banner_url, "category": category,
                                                "state": state, "city": city, "address": address, "total_capacity": total_capacity, "available_tickets": total_capacity,
                                                "start_date": start_date, "end_date": end_date})
        await conn.commit()

        # Fetch the id of the recently added event and return it
        query = await conn.execute(text("SELECT id FROM events WHERE id = LAST_INSERT_ID()"))
        event_id = query.scalar() # Convert from row to int
        return event_id


async def get_event_by_id(event_id: int) -> dict | None:
    """
    Fetch an event by ID from the database.
    
    Args:
        event_id: Event ID
    
    Returns:
        dict or None: Event data or None if not found
    """
    async with engine.connect() as conn:
        query = await conn.execute(text("SELECT * FROM events WHERE id = :event_id"), {"event_id": event_id})
        results = query.mappings().one_or_none() # Convert from row to dict

        return results


async def get_all_events(
    category: str | None = None,
    city: str | None = None,
    state: str | None = None,
    page: int = 1
) -> tuple[list[dict], int]:
    """
    Fetch all events with optional filters and pagination.
    
    Args:
        category: Filter by category (optional)
        city: Filter by city (optional)
        state: Filter by state (optional)
        page: Page number (default 1)
    
    Returns:
        tuple: (list of event dicts, total count)
    """
    # Create a dynamic query that changes based on the filter selected
    query = "SELECT * FROM events WHERE 1=1"
    params = {}

    if category:
        query += " AND category = :category"
        params["category"] = category
    if city:
        query += " AND city = :city"
        params["city"] = city
    if state:
        query += " AND state = :state"
        params["state"] = state

    # Pagination
    items_per_page = 10
    offset = (page - 1) * items_per_page

    # Connect to database
    async with engine.connect() as conn:
        # Count total events matching selected filters
        count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
        count_result = await conn.execute(text(count_query), params)
        total_events = count_result.scalar()

        # Get event info for each event found (for those that fall under the selected filters)
        paginated_query = query + " ORDER BY id ASC LIMIT :limit OFFSET :offset"
        params["limit"] = items_per_page
        params["offset"] = offset

        result = await conn.execute(text(paginated_query), params)
        events = result.mappings().all()

        # Convert each event from a row to a dict, and add it to a list
        event_list = [dict(event_row) for event_row in events]

    # Calculate total pages
    total_pages = (total_events + items_per_page - 1) // items_per_page

    # Return tuple with all filtered event's info (inside the list) and a total pages count
    return (event_list, total_pages)

async def get_events_by_organizer(organizer_id: int) -> list[dict]:
    """
    Fetch all events created by a specific organizer.
    
    Args:
        organizer_id: User ID of organizer
    
    Returns:
        list: List of event dicts
    """
    async with engine.connect() as conn:
        query = await conn.execute(text("SELECT * FROM events WHERE organizer_id = :organizer_id"), {"organizer_id": organizer_id})
        events = query.mappings().all()

        # Convert each event in events from row to a dict, and add it to a list
        event_list = [dict(event_row) for event_row in events]

        # Return list with all events made by "organizer_id"
        return event_list


async def update_event(
    event_id: int,
    organizer_id: int,
    title: str | None = None,
    description: str | None = None,
    banner_url: str | None = None,
    category: str | None = None,
    state: str | None = None,
    city: str | None = None,
    address: str | None = None,
    total_capacity: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> bool:
    """
    Update an event (only by organizer).
    """
    async with engine.connect() as conn:
        # Search DB for event to be updated and check organizer credential
        query = await conn.execute(
            text("SELECT * FROM events WHERE id = :event_id AND organizer_id = :organizer_id"), 
            {"event_id": event_id, "organizer_id": organizer_id}
        )
        existing_event = query.mappings().one_or_none()

        # If not found or organizer_id doesn't match, return ValueError
        if not existing_event:
            raise ValueError("Evento não encontrado ou unauthorized.")

        # Build dynamic query where only the fields which were chosen to be changed get updated
        updates = []
        params = {"event_id": event_id}

        if title:
            updates.append("title = :title")
            params["title"] = title

        if description:
            updates.append("description = :description")
            params["description"] = description

        if banner_url:
            updates.append("banner_url = :banner_url")
            params["banner_url"] = banner_url

        if category:
            updates.append("category = :category")
            params["category"] = category

        # Verify if state, city or address actually CHANGED from the database values
        location_changed = False

        if state is not None and state.strip() and state.strip() != existing_event.get("state"):
            location_changed = True

        if city is not None and city.strip() and city.strip() != existing_event.get("city"):
            location_changed = True

        if address is not None and address.strip() and address.strip() != existing_event.get("address"):
            location_changed = True

        # Now validate ONLY if the location has actually changed.
        if location_changed:
            event_start = start_date if start_date else existing_event["start_date"]

            # Make event_start timezone-aware if it's naive
            if isinstance(event_start, datetime) and not event_start.tzinfo:
                event_start = event_start.replace(tzinfo=timezone.utc)

            days_until_start = (event_start - datetime.now(timezone.utc)).days

            if days_until_start < 30:
                raise ValueError("A localização só pode ser alterada com 30 dias de antecedência.")
        
        # If the location has changed and passed validation, add it to the updates.
        if state is not None and state.strip():
            updates.append("state = :state")
            params["state"] = state

        if city is not None and city.strip():
            updates.append("city = :city")
            params["city"] = city

        if address:
            updates.append("address = :address")
            params["address"] = address

        if total_capacity:
            # Check if the new total_capacity is not less than the number of tickets already sold (prevent scams).
            sold_query = await conn.execute(
                text("SELECT COALESCE(SUM(quantity_sold), 0) as total_sold FROM ticket_types WHERE event_id = :event_id"), 
                {"event_id": event_id}
            )
            total_sold = sold_query.scalar()

            # If it is, return ValueError
            if total_capacity < total_sold:
                raise ValueError("Não é possível reduzir a capacidade para um nível inferior ao de ingressos já vendidos.")
            else:
                # Else, update
                updates.append("total_capacity = :total_capacity")
                params["total_capacity"] = total_capacity

        # Convert start_date and end_date to aware if they're datetime objects and are provided
        if isinstance(start_date, datetime) and not start_date.tzinfo:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if isinstance(end_date, datetime) and not end_date.tzinfo:
            end_date = end_date.replace(tzinfo=timezone.utc)

        if start_date:
            # Check if the start date is changed to before today
            now = datetime.now(timezone.utc)
            
            if start_date < now:
                raise ValueError("Não é possível alterar a data de início de um evento que já começou.")
            else:
                # Else, update
                updates.append("start_date = :start_date")
                params["start_date"] = start_date

        if end_date:
            # Check if the event end_date is early than the event's current start_date
            event_start = start_date if start_date else existing_event["start_date"]
            
            # Make event_start timezone-aware if it's naive
            if isinstance(event_start, datetime) and not event_start.tzinfo:
                event_start = event_start.replace(tzinfo=timezone.utc)
            
            if end_date < event_start:
                raise ValueError("A nova data de término do evento não pode ser anterior à data de início original.")
            else:
                # Else, update
                updates.append("end_date = :end_date")
                params["end_date"] = end_date

        if start_date and end_date and end_date < start_date:
            # Check if the event new end_date is early than the new start_date
            raise ValueError("A nova data de término do evento não pode ser anterior à nova data de início.")

        if not updates:
            # If there aren't any updates, just return True
            return True

        query = f"UPDATE events SET {', '.join(updates)} WHERE id = :event_id"

        # UPDATE new information into the database
        await conn.execute(text(query), params)
        await conn.commit()

        # Return success
        return True 


async def delete_event(event_id: int, organizer_id: int) -> bool:
    """
    Delete an event (only by organizer).
    
    Args:
        event_id: Event ID
        organizer_id: User ID (must be the organizer)
    
    Returns:
        bool: True if successful
    
    Raises:
        ValueError: If unauthorized or event not found
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for ownership of the current user
        query = await conn.execute(text("SELECT * FROM events WHERE id = :event_id AND organizer_id = :organizer_id"), {"event_id": event_id, "organizer_id": organizer_id})
        existing_event = query.mappings().one_or_none()

        # If event not found or the current user isn't the event organizer, return ValueError
        if not existing_event:
            raise ValueError("Evento não encontrado ou unauthorized.")

        # Else, delete the event and return True
        await conn.execute(text("DELETE FROM events WHERE id = :event_id"), {"event_id": event_id})
        await conn.commit()

        return True


# ==========================================
# TICKET TYPE (LOTES/TICKET BATCHES) DATABASE OPERATIONS
# ==========================================

async def create_ticket_type(
    event_id: int,
    type: str,
    price: int,
    quantity_available: int
) -> int:
    """
    Create a new ticket type (ticket batch) for an event.
    
    Args:
        event_id: Event ID
        type: Ticket type (standard, vip, early_bird, group)
        price: Price in normal value (e.g., R$ 100,00)
        quantity_available: Number of tickets available
    
    Returns:
        int: The newly created ticket type's ID
    """
    # Connect to database
    async with engine.connect() as conn:
        # INSERT ticket type into DB
        ticket_query = """
        INSERT INTO ticket_types (event_id, type, price, quantity_available)
        VALUES (:event_id, :type, :price, :quantity_available)
        """
        await conn.execute(text(ticket_query), {"event_id": event_id, "type": type, "price": price, "quantity_available": quantity_available})
        await conn.commit()

        # Fetch the id of the recently added ticket type and return it
        query = await conn.execute(text("SELECT id FROM ticket_types WHERE id = LAST_INSERT_ID()"))
        ticket_type_id = query.scalar()

        return ticket_type_id


async def get_ticket_types_by_event(event_id: int) -> list[dict]:
    """
    Fetch all ticket types for an event.
    
    Args:
        event_id: Event ID
    
    Returns:
        list: List of ticket type dicts
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for ticket types of a event
        query = await conn.execute(text("SELECT * FROM ticket_types WHERE event_id = :event_id"), {"event_id": event_id})
        results = query.mappings().all()

        # Convert them and add them to a list
        ticket_types_list = [dict(results_row) for results_row in results]

        # Return the list
        return ticket_types_list


async def get_ticket_type_by_id(ticket_type_id: int) -> dict | None:
    """
    Fetch a single ticket type by ID.
    
    Args:
        ticket_type_id: Ticket type ID
    
    Returns:
        dict or None: Ticket type data or None if not found
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for ticket_type of id 'ticket_type_id'
        query = await conn.execute(text("SELECT * FROM ticket_types WHERE id = :ticket_type_id"), {"ticket_type_id": ticket_type_id})
        results = query.mappings().one_or_none()

        # Return ticket_type info dict (or None if not found)
        return results


async def update_ticket_type(
    ticket_type_id: int,
    type: str | None = None,
    price: int | None = None
) -> bool:
    """
    Update ticket type details (price/type only, not quantity).
    
    Note: quantity_available NOT included — it's managed through ticket sales
    
    Args:
        ticket_type_id: Ticket type ID
        type: New type (optional)
        price: New price in normal value (optional)
    
    Returns:
        bool: True if successful
    """
    async with engine.connect() as conn:
        updates = []
        params = {"ticket_type_id": ticket_type_id}

        if type:
            updates.append("type = :type")
            params["type"] = type

        if price:
            updates.append("price = :price")
            params["price"] = price

        if not updates:
            # If there wan't any updates, just return True for what's current registered
            return True

        # Base query with all selected updates
        query = f"UPDATE ticket_types SET {', '.join(updates)} WHERE id = :ticket_type_id"
        
        # UPDATE new information into the database
        await conn.execute(text(query), params)
        await conn.commit()

        # Return success
        return True


async def delete_ticket_type(ticket_type_id: int) -> bool:
    """
    Delete a ticket type (only if no tickets sold).

    Args:
        ticket_type_id: Ticket type ID
    
    Returns:
        bool: True if successful
    
    Raises:
        ValueError: If tickets were already sold, ticket type not found or error during ticket type deletion
    """
    async with engine.connect() as conn:
        # Search DB for any tickets sold under ticket_type
        query = await conn.execute(text("SELECT quantity_sold FROM ticket_types WHERE id = :ticket_type_id"), {"ticket_type_id": ticket_type_id})
        existing_ticket_type = query.mappings().one_or_none()

        # If it doesn't exist, raise ValueError
        if not existing_ticket_type:
            raise ValueError("Lote não encontrado ou não existe.")

        # If there is already sold tickets under ticket type, raise ValueError
        if existing_ticket_type["quantity_sold"] > 0:
            raise ValueError("Não é possível deletar lote: ingressos já foram vendidos sob ele.")
        # Delete the ticket type
        await conn.execute(text("DELETE FROM ticket_types WHERE id = :ticket_type_id"), {"ticket_type_id": ticket_type_id})
        await conn.commit()

        # Else, return True
        return True