from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text

from app.config import templates
from app.database import engine
from app.schemas.schemas import EventCreate, EventUpdate, TicketTypeCreate
from app.services.audit_service import (
    get_ip_from_request,
    get_user_agent_from_request,
    log_action,
    prepare_old_new_values,
)
from app.services.auth_service import get_current_user_optional, verify_user_token
from app.services.event_service import (
    create_event,
    create_ticket_type,
    delete_event,
    delete_ticket_type,
    get_all_events,
    get_event_by_id,
    get_events_by_organizer,
    get_ticket_type_by_id,
    get_ticket_types_by_event,
    update_event,
)
from app.services.image_service import delete_banner_image, upload_banner_image

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
    event_data: Annotated[EventCreate, Form()] = None,
):
    """
    Create a new event (requires login).
    """
    if not event_data:
        raise HTTPException(status_code=400, detail="Invalid form data. Please fill all required fields.")

    # Extract banner file from form manually
    form_data = await request.form()
    banner_file = form_data.get("banner_file")

    # Handle banner upload
    banner_url = None
    if banner_file and banner_file.filename:
        try:
            banner_url = await upload_banner_image(banner_file)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Add event to the database
    try:
        event_id = await create_event(
            organizer_id=user_id,
            title=event_data.title,
            description=event_data.description,
            banner_url=banner_url,
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

    # ==== AUDIT LOGS ENTRY ====
    new_values_dict = {
        "title": event_data.title,
        "description": event_data.description,
        "banner_url": banner_url,
        "category": event_data.category,
        "state": event_data.state,
        "city": event_data.city,
        "address": event_data.address,
        "total_capacity": event_data.total_capacity,
        "start_date": event_data.start_date.isoformat() if event_data.start_date else None,
        "end_date": event_data.end_date.isoformat() if event_data.end_date else None
    }

    _, new_values_json = prepare_old_new_values(None, new_values_dict)

    try:
        await log_action(
            action="create",
            auditable_type="event",
            auditable_id=event_id,
            user_id=user_id,
            old_values=None,
            new_values=new_values_json,
            ip_address=get_ip_from_request(request),
            user_agent=get_user_agent_from_request(request)
        )
    except ValueError:
        pass
    # ==== END OF AUDIT LOGS ENTRY ====

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
# ORGANIZER EVENT MANAGEMENT (EDIT / DELETE)
# ==========================================

@router.get("/{event_id}/edit", response_class=HTMLResponse)
async def get_edit_event(
    request: Request,
    event_id: int,
    user_id: int = Depends(verify_user_token)
):
    """
    Render event edit form.
    """
    # Fetch event
    event = await get_event_by_id(event_id)

    # Check if exists
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or doesn't exist.")
    
    # Check if user is event organizer, else return 403
    if event["organizer_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access Forbidden: You aren't allowed to view this page or perform an action.")
    
    # Render template with event data
    return templates.TemplateResponse(
        request,
        "edit_event.html",
        {
            "request": request,
            "event": event,
            "user_id": user_id
        }
    )

@router.post("/{event_id}/edit", response_class=HTMLResponse)
async def post_edit_event(
    request: Request,
    event_id: int,
    user_id: int = Depends(verify_user_token),
    event_data: Annotated[EventUpdate, Form()] = None
):
    """
    Update event information.
    """
    # Check if event_data is None
    if not event_data:
        raise HTTPException(status_code=400, detail="Invalid form data.")

    # Get current event data first (for audit logs old values)
    old_event_data = await get_event_by_id(event_id)

    # Check if the events exists
    if not old_event_data:
        raise HTTPException(status_code=404, detail="Event not found or doesn't exist.")

    # Check if the current user is the event organizer
    if old_event_data['organizer_id'] != user_id:
        raise HTTPException(status_code=403, detail="Access Forbidden: You aren't allowed to view this page.")

    # Extract banner file from form manually
    form_data = await request.form()
    banner_file = form_data.get("banner_file")

    # Handle banner upload (delete old, upload new)
    banner_url = None
    if banner_file and banner_file.filename:
        try:
            # Delete old banner if exists
            if old_event_data["banner_url"]:
                try:
                    await delete_banner_image(old_event_data["banner_url"])
                except ValueError:
                    pass
            
            # Upload new banner
            banner_url = await upload_banner_image(banner_file)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Build dynamic dict that only store info of the fields that were chosen to be updated
    update_params = {
        "event_id": event_id,
        "organizer_id": user_id
    }

    if event_data.title:
        update_params["title"] = event_data.title
    if event_data.description:
        update_params["description"] = event_data.description
    if event_data.category:
        update_params["category"] = event_data.category
    if event_data.state:
        update_params["state"] = event_data.state
    if event_data.city:
        update_params["city"] = event_data.city
    if event_data.address:
        update_params["address"] = event_data.address
    if event_data.total_capacity:
        update_params["total_capacity"] = event_data.total_capacity
    if event_data.start_date:
        update_params["start_date"] = event_data.start_date
    if event_data.end_date:
        update_params["end_date"] = event_data.end_date
    if banner_url:
        update_params["banner_url"] = banner_url

    # Update event info
    try:
        await update_event(**update_params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ==== AUDIT LOGS ENTRY ====
    # Convert datetimes to ISO string before passing for audit logs
    old_event_data_audit = {
        "title": old_event_data["title"],
        "description": old_event_data["description"],
        "banner_url": old_event_data["banner_url"],
        "category": old_event_data["category"],
        "state": old_event_data["state"],
        "city": old_event_data["city"],
        "address": old_event_data["address"],
        "total_capacity": old_event_data["total_capacity"],
        "start_date": old_event_data["start_date"].isoformat() if old_event_data["start_date"] else None,
        "end_date": old_event_data["end_date"].isoformat() if old_event_data["end_date"] else None
    }

    # Create a new dict to store new values
    new_dict = {}

    # Dynamic addition, only adds to the log the fields that were updated
    if event_data.title:
        new_dict["title"] = event_data.title
    if event_data.description:
        new_dict["description"] = event_data.description
    if event_data.category:
        new_dict["category"] = event_data.category
    if event_data.state:
        new_dict["state"] = event_data.state
    if event_data.city:
        new_dict["city"] = event_data.city
    if event_data.address:
        new_dict["address"] = event_data.address
    if event_data.total_capacity:
        new_dict["total_capacity"] = event_data.total_capacity
    if event_data.start_date:
        new_dict["start_date"] = event_data.start_date.isoformat() if event_data.start_date else None
    if event_data.end_date:
        new_dict["end_date"] = event_data.end_date.isoformat() if event_data.end_date else None
    if banner_url:
        new_dict["banner_url"] = banner_url

    # Convert from dict to JSON string
    old_values_json, new_values_json = prepare_old_new_values(old_event_data_audit, new_dict)

    # Log action
    try:
        await log_action(
            action='update',
            auditable_type='event',
            auditable_id=event_id,
            user_id=user_id,
            old_values=old_values_json,
            new_values=new_values_json,
            ip_address=get_ip_from_request(request),
            user_agent=get_user_agent_from_request(request)
        )
    except ValueError:
        pass
    # ==== END OF AUDIT LOGS ENTRY ====

    # Flash message
    request.session["flash"] = "Event updated successfully."

    # Redirect back to event details page
    return RedirectResponse(url=f"/events/{event_id}", status_code=303)

@router.post("/{event_id}/delete", response_class=HTMLResponse)
async def delete_event_route(
    request: Request,
    event_id: int,
    user_id: int = Depends(verify_user_token)
):
    """Delete event."""
    # Get event first (for audit logs)
    event_data = await get_event_by_id(event_id)

    # Check if event exists, else 404
    if not event_data:
        raise HTTPException(status_code=404, detail="Event not found or doesn't exist.")

    # Check if the current user is the event organizer
    if event_data["organizer_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access Forbidden: You aren't allowed to perform this action.")
    
    # Delete the event
    try:
        is_deleted = await delete_event(event_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # If the event couldn't be deleted, return error message (fallback in case except doesn't do it)
    if not is_deleted:
        raise HTTPException(status_code=400, detail="An error occurred while deleting your event from the database. Please try again later.")

    # ==== AUDIT LOGS ENTRY ====
    # Fix datetime dates for start and end date to work well on the audit log
    start_date_iso = event_data["start_date"].isoformat()
    end_date_iso = event_data["end_date"].isoformat()
    
    # Add those all old values to a new dict
    old_dict = {
        "title": event_data["title"],
        "description": event_data["description"],
        "banner_url": event_data["banner_url"],
        "category": event_data["category"],
        "state": event_data["state"],
        "city": event_data["city"],
        "address": event_data["address"],
        "total_capacity": event_data["total_capacity"],
        "start_date": start_date_iso,
        "end_date": end_date_iso
    }

    # Convert current event info from dict to JSON string
    old_values_json, _ = prepare_old_new_values(old_dict, None)

    # Log action
    try:
        await log_action(
            action='delete',
            auditable_type='event',
            auditable_id=event_id,
            user_id=user_id,
            old_values=old_values_json,
            new_values=None,
            ip_address=get_ip_from_request(request),
            user_agent=get_user_agent_from_request(request)
        )
    except ValueError:
        pass
    # ==== END OF AUDIT LOGS ENTRY ====
    # Flash + redirect to /events/my-events
    request.session["flash"] = "Event deleted successfully."

    return RedirectResponse(url="/events/my-events", status_code=303)


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

    # ==== AUDIT LOGS ENTRY ====
    # Fetch id of the recently created ticket type
    async with engine.connect() as conn:
        query = await conn.execute(text("SELECT id FROM ticket_types WHERE id = LAST_INSERT_ID()"))
        ticket_type_id = query.scalar()

    # Fetch ticket type data info
    new_values_dict = {
        "type": ticket_data.type,
        "price": ticket_data.price,
        "quantity_available": ticket_data.quantity_available
    }

    # Convert from dict to JSON string
    _, new_values_json = prepare_old_new_values(None, new_values_dict)

    # Log action
    try:
        await log_action(
            action="create",
            auditable_type="ticket_type",
            auditable_id=ticket_type_id,
            user_id=user_id,
            old_values=None,
            new_values=new_values_json,
            ip_address=get_ip_from_request(request),
            user_agent=get_user_agent_from_request(request)
        )
    except ValueError:
        pass
    # ==== END OF AUDIT LOGS ENTRY ====

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

    # ==== AUDIT LOGS ENTRY ====
    # Fetch all ticket type data
    old_value_dict = {
        "id": ticket_type["id"],
        "event_id": ticket_type["event_id"],
        "type": ticket_type["type"],
        "price": ticket_type["price"],
        "quantity_available": ticket_type["quantity_available"],
        "quantity_sold": ticket_type["quantity_sold"],
        "created_at": ticket_type["created_at"]
    }

    # Convert them from dict to JSON string
    old_values_json, _ = prepare_old_new_values(old_value_dict, None)

    # Log action
    try:
        await log_action(
            action="delete",
            auditable_type="ticket_type",
            auditable_id=ticket_type_id,
            user_id=user_id,
            old_values=old_values_json,
            new_values=None,
            ip_address=get_ip_from_request(request),
            user_agent=get_user_agent_from_request(request)
        )
    except ValueError:
        pass
    # ==== END OF AUDIT LOGS ENTRY ====

    # Delete ticket type, if it has already sold any tickets under it, return 400
    try:
        await delete_ticket_type(ticket_type_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Impossible to delete ticket type when tickets have already been sold.")

    # Flash message
    request.session["flash"] = "Ticket type successfully deleted."

    # Redirect to events lotes page
    return RedirectResponse(url=f"/events/{event_id}/lotes", status_code=303)