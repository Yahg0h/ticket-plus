from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import templates
from app.schemas.schemas import EventCreate, TicketTypeCreate
from app.services.auth_service import get_current_user_optional, verify_user_token
from app.services.event_service import (
    create_event,
    create_ticket_type,
    delete_ticket_type,
    get_all_events,
    get_event_by_id,
    get_events_by_organizer,
    get_ticket_type_by_id,
    get_ticket_types_by_event,
)

# Configure router
router = APIRouter(prefix="/events", tags=["events"])

# ==========================================
# PUBLIC EVENT ROUTES
# ==========================================

@router.get("", response_class=HTMLResponse)
async def list_all_events(
    request: Request,
    user_id: int | None = Depends(get_current_user_optional),
    category: str | None = Query(None),
    city: str | None = Query(None),
    state: str | None = Query(None),
    page: int = Query(1, ge=1)
):
    """
    Render public events showcase (vitrine) with filters and pagination.
    """
    # Get all events filtered
    events = await get_all_events(category, city, state, page)

    # Get event_list and total count of events inside the list
    event_list, total = events
    # Total pages to see all events
    total_pages = (total + 9) // 10

    # Return info to be rendered in events_list.html
    return templates.TemplateResponse(
        request,
        "events_list.html",
        {
            "request": request,
            "events": event_list,
            "user_id": user_id,
            "page": page,
            "total_pages": total_pages,
            "category": category,
            "city": city,
            "state": state,
        }
    )

# ==========================================
# ORGANIZER EVENT ROUTES
# ==========================================

@router.get("/my-events", response_class=HTMLResponse)
async def list_my_events(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Render organizer's events dashboard (requires login).
    """
    # Fetch all events made by the current user
    events = await get_events_by_organizer(user_id)

    # Render my_events.html with all events made by the user
    return templates.TemplateResponse(
        request,
        "my_events.html",
        {
            "request": request,
            "events": events,
            "user_id": user_id,
            "now": datetime.now() # Helps show correct event badge status in my_events.html
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def get_create_event(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Render event creation form (requires login).
    """
    # Renders create_event.html
    return templates.TemplateResponse(
        request,
        "create_event.html",
        {
            "request": request,
            "user_id": user_id
        }
    )


@router.post("/create", response_class=HTMLResponse)
async def post_create_event(
    request: Request,
    user_id: int = Depends(verify_user_token),
    event_data: Annotated[EventCreate, Form()] = None
):
    """
    Create a new event (requires login).
    """
    # Add event to the database; if a error happens, return 400
    try:
        event_id = await create_event(
            organizer_id=user_id,
            title=event_data.title,
            description=event_data.description,
            banner_url=event_data.banner_url,
            category=event_data.category,
            state=event_data.state,
            city=event_data.city,
            address=event_data.address,
            total_capacity=event_data.total_capacity,
            start_date=event_data.start_date,
            end_date=event_data.end_date
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="An error occurred during the database event creation operation. Please check the entered data and try again, or try again later.")
    except Exception:
        raise HTTPException(status_code=400, detail="An error occurred during the database event creation operation. Please check the entered data and try again, or try again later.")

    # Flash message
    request.session["flash"] = "Event created successfully!"

    # Redirect to the event_id lotes (ticket batch) section to configure tickets
    return RedirectResponse(url=f"/events/{event_id}/lotes", status_code=303)


# ==========================================
# PUBLIC EVENT DETAILS ROUTE
# ==========================================

@router.get("/{event_id}", response_class=HTMLResponse)
async def get_event_detail(
    request: Request,
    event_id: int,
    user_id: int | None = Depends(get_current_user_optional)
):
    """
    Render event detail page with ticket types.
    """
    # Get event info
    event = await get_event_by_id(event_id)

    # If the event doesn't exist, return 404
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or doesn't exist.")

    # Fetch ticket types for the event
    ticket_types = await get_ticket_types_by_event(event_id)

    # Render the event_detail.html with all event info
    return templates.TemplateResponse(
        request,
        "event_detail.html",
        {
            "request": request,
            "event": event,
            "ticket_types": ticket_types,
            "user_id": user_id
        }
    )
    

# ==========================================
# TICKET TYPE (LOTES/Ticket Batches) ROUTES
# ==========================================

@router.get("/{event_id}/lotes", response_class=HTMLResponse)
async def get_add_ticket_types(
    request: Request,
    event_id: int,
    user_id: int = Depends(verify_user_token)
):
    """
    Render ticket types management page (requires login).
    """
    # Fetch event info
    event = await get_event_by_id(event_id)

    # If event doesn't exist, return 404
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or doesn't exist.")

    # If current user isn't the event organizer, return 403
    if event["organizer_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access Forbidden: You aren't allowed to access this page.")

    # Get ticket_types for this event
    ticket_types = await get_ticket_types_by_event(event_id)

    # Render manage_ticket_types.html with all event info
    return templates.TemplateResponse(
        request,
        "manage_ticket_types.html",
        {
            "request": request,
            "event": event,
            "ticket_types": ticket_types,
            "user_id": user_id
        }
    )


@router.post("/{event_id}/lotes", response_class=HTMLResponse)
async def post_add_ticket_type(
    request: Request,
    event_id: int,
    user_id: int = Depends(verify_user_token),
    ticket_data: Annotated[TicketTypeCreate, Form()] = None
):
    """
    Add a new ticket type to an event (requires login).
    """
    event = await get_event_by_id(event_id)

    # If event doesn't exist, return 404
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or doesn't exist.")

    # If current user isn't the event organizer, return 403
    if event["organizer_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access Forbidden: You aren't allowed to access this page.")

    # Add a new ticket type to the database; if a ValueError happens, return 400
    try:
        await create_ticket_type(
            event_id=event_id,
            type=ticket_data.type,
            price=ticket_data.price,
            quantity_available=ticket_data.quantity_available
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="An error occurred during the database event ticket type creation operation. Please check the entered data and try again, or try again later.")

    # Flash message
    request.session["flash"] = "Lote/Ticket Batch successfully added!"

    # Redirect to event lotes page
    return RedirectResponse(url=f"/events/{event_id}/lotes", status_code=303)

@router.post("/{event_id}/lotes/{ticket_type_id}/delete", response_class=HTMLResponse)
async def delete_ticket_type_route(
    request: Request,
    event_id: int,
    ticket_type_id: int,
    user_id: int = Depends(verify_user_token)
):
    """
    Delete a ticket type from an event (requires login).
    """
    # Fetch event info
    event = await get_event_by_id(event_id)

    # If event doesn't exist, return 404
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or doesn't exist.")

    # If current user isn't the event organizer, return 403
    if event["organizer_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access Forbidden: You aren't allowed to access this page.")

    # Fetch event ticket_type info
    ticket_type = await get_ticket_type_by_id(ticket_type_id)

    # If ticket type doesn't exist, return 404
    if not ticket_type:
        raise HTTPException(status_code=404, detail="Ticket type not found or doesn't exist.")

    # Delete ticket type, if it has already sold any tickets under it, return 400
    try:
        await delete_ticket_type(ticket_type_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Impossible to delete ticket type when tickets have already been sold.")

    # Flash message
    request.session["flash"] = "Ticket type successfully deleted."

    # Redirect to events lotes page
    return RedirectResponse(url=f"/events/{event_id}/lotes", status_code=303)