from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.config import templates
from app.services.audit_service import (
    get_ip_from_request,
    get_user_agent_from_request,
    log_action,
    prepare_old_new_values,
)
from app.services.auth_service import verify_user_token
from app.services.order_service import get_order_by_id
from app.services.ticket_service import (
    check_ticket_ownership,
    create_ticket,
    generate_ticket_pdf,
    get_order_tickets_count,
    get_ticket_by_id,
    get_tickets_by_buyer,
    get_tickets_by_order,
    update_ticket_holder,
)

# Configure router
router = APIRouter(prefix="/tickets", tags=["tickets"])

# ==========================================
# TICKET HOLDER DATA COLLECTION ROUTES
# ==========================================

@router.get("/collect/{order_id}", response_class=HTMLResponse)
async def get_collect_holder_data(
    request: Request,
    order_id: int,
    user_id: int = Depends(verify_user_token)
):
    """
    Render form to collect ticket holder data (name and CPF) for each ticket in an order.
    
    Args:
        request: FastAPI Request object
        order_id: Order ID
        user_id: Current user ID (from dependency)
    
    Returns:
        TemplateResponse: Rendered collect_holder_data.html
    """
    # Fetch order information
    order = await get_order_by_id(order_id)

    # Check if the order doesn't exist, return 404
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or doesn't exist.")

    # Check if the buyer of the order is the same person as the current user, if not, return 403
    if order["buyer_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access Forbidden: You aren't allowed to view the expected page.")

    # Count the tickets bought under the order_id
    ticket_count = await get_order_tickets_count(order_id)

    # Return all information to be rendered in collect_holder_data.html
    return templates.TemplateResponse(
        request,
        "collect_holder_data.html",
        {
            "request": request,
            "order": order,
            "ticket_count": ticket_count,
            "user_id": user_id
        }
    )


@router.post("/collect/{order_id}", response_class=HTMLResponse)
async def post_collect_holder_data(
    request: Request,
    order_id: int,
    user_id: int = Depends(verify_user_token)
):
    """
    Process ticket holder data collection and create tickets.
    
    Args:
        request: FastAPI Request object
        order_id: Order ID
        user_id: Current user ID (from dependency)
    
    Returns:
        RedirectResponse: Redirect to /tickets
    """
    # Fetch order info
    order = await get_order_by_id(order_id)

    # If the order isn't found, return 404
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or doesn't exist.")

    # Check if the buyer of the order is the same person as the current user, if not, return 403
    if order["buyer_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access Forbidden: You don't have access to view this page.")

    # Get form data in dynamic form
    form_data = await request.form()

    # Fetch existing tickets for this order
    existing_tickets = await get_tickets_by_order(order_id)

    # If no tickets exist, create them first
    if len(existing_tickets) == 0:
        price_per_ticket = order["total_amount"] // order["quantity"]
        for i in range(order["quantity"]):
            await create_ticket(
                order_id=order_id,
                ticket_type_id=order["ticket_type_id"],
                holder_name="Placeholder",
                holder_cpf="000.000.000-00",
                price_paid=price_per_ticket
            )
        # Fetch tickets again
        existing_tickets = await get_tickets_by_order(order_id)

    # Check if quantity matches
    if len(existing_tickets) != order["quantity"]:
        raise HTTPException(status_code=400, detail="Ticket count mismatch. Please contact support.")

    # Loop each ticket and update with form data
    for i, ticket in enumerate(existing_tickets, start=1):
        # Extract form data dynamically
        holder_name = form_data.get(f"holder_name_{i}")
        holder_cpf = form_data.get(f"holder_cpf_{i}")

        # Validate the holder data
        if not holder_name or not holder_cpf:
            raise HTTPException(status_code=400, detail=f"Missing data for ticket {i}")

        # UPDATE ticket with real data
        await update_ticket_holder(
            ticket_id=ticket["id"],
            holder_name=holder_name,
            holder_cpf=holder_cpf
        )

        # ==== AUDIT LOGS ENTRY ====
        # Fetch old ticket holder data
        old_dict = {
            "holder_name": ticket["holder_name"],
            "holder_cpf": ticket["holder_cpf"]
        }

        # Fetch new ticket holder data
        new_dict = {
            "holder_name": holder_name,
            "holder_cpf": holder_cpf
        }

        # Convert from dict to JSON string
        old_values_json, new_values_json = prepare_old_new_values(old_dict, new_dict)

        # Log action (for each ticket)
        try:
            await log_action(
                action='update',
                auditable_type='ticket',
                auditable_id=ticket["id"],
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
    request.session["flash"] = "Holder data updated successfully!"

    # Redirect back to tickets page
    return RedirectResponse(url="/tickets", status_code=303)


# ==========================================
# MY TICKETS LISTING ROUTE
# ==========================================

@router.get("", response_class=HTMLResponse)
async def list_my_tickets(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Render user's ticket list (GET /tickets).
    
    Args:
        request: FastAPI Request object
        user_id: Current user ID (from dependency)
    
    Returns:
        TemplateResponse: Rendered my_tickets.html
    """
    # Fetch all tickets owned by the buyer
    tickets = await get_tickets_by_buyer(user_id)

    # Return all info to be rendered in my_tickets.html
    return templates.TemplateResponse(
        request,
        "my_tickets.html",
        {
            "request": request,
            "tickets": tickets,
            "user_id": user_id
        }
    )


# ==========================================
# TICKET DETAIL & PDF ROUTES
# ==========================================

@router.get("/{ticket_id}", response_class=HTMLResponse)
async def view_ticket(
    request: Request,
    ticket_id: int,
    user_id: int = Depends(verify_user_token)
):
    """
    Render ticket detail page (view ticket info + download PDF button).
    
    Args:
        request: FastAPI Request object
        ticket_id: Ticket ID
        user_id: Current user ID (from dependency)
    
    Returns:
        TemplateResponse: Rendered ticket_detail.html
    """
    # Fetch ticket info
    ticket = await get_ticket_by_id(ticket_id)

    # If the ticket isn't found, return 404
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found or doesn't exist.")

    # Check if the current user is the owner/buyer of the ticket
    is_owner = await check_ticket_ownership(ticket_id, user_id)

    # If not, return 403
    if not is_owner:
        raise HTTPException(status_code=403, detail="Access Forbidden: You aren't allowed to view this page.")

    # Get all info about the order the ticket was purchased on
    order = await get_order_by_id(ticket["order_id"])

    # Return all info to be rendered in ticket_detail.html
    return templates.TemplateResponse(
        request,
        "ticket_detail.html",
        {
            "request": request,
            "ticket": ticket,
            "order": order,
            "user_id": user_id
        }
    )


@router.get("/{ticket_id}/pdf")
async def download_ticket_pdf(
    ticket_id: int,
    user_id: int = Depends(verify_user_token)
):
    """
    Generate and download ticket PDF with QR code.
    
    Args:
        ticket_id: Ticket ID
        user_id: Current user ID (from dependency)
    
    Returns:
        FileResponse: PDF file download
    """
    # Check if the current user is the owner/buyer of the ticket
    is_owner = await check_ticket_ownership(ticket_id, user_id)

    # If not return 403
    if not is_owner:
        raise HTTPException(status_code=403, detail="Access Forbidden: You aren't allowed to perform this action or view this page.")

    # Else, generate PDF
    try:
        pdf_bytes = await generate_ticket_pdf(ticket_id)
    except ValueError:
        raise HTTPException(status_code=500, detail="A error occurred while generating the ticket PDF. Please try again.")

    # Return FileResponse with the PDF to be shown
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ticket_{ticket_id}.pdf"}
    )