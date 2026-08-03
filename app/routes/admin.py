"""
Admin routes for TicketPlus.
"""
 
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text

from app.config import templates
from app.database import engine
from app.services.audit_service import get_audit_logs, log_action
from app.services.auth_service import get_user_by_id, verify_user_token

router = APIRouter(prefix="/admin", tags=["admin"])
 
# ===== DEPENDENCY: Verify if it is a admin =====
async def verify_admin(
    user_id: int = Depends(verify_user_token),
) -> int:
    """
    Verify if user is admin.
    """
    user = await get_user_by_id(user_id)
    
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access Denied: Admin only")
    
    return user_id
 
# ===== MAIN DASHBOARD =====
 
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin_id: int = Depends(verify_admin)
):
    """
    Main admin dashboard.
    """
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "request": request,
            "user_id": admin_id
        }
    )
 
# ===== AUDIT LOGS =====
 
@router.get("/audit-logs", response_class=HTMLResponse)
async def get_audit_logs_dashboard(
    request: Request,
    admin_id: int = Depends(verify_admin),
    page: int = 1,
    user_filter: int | None = None,
    action_filter: str | None = None,
    type_filter: str | None = None
):
    """
    Display audit logs dashboard with filters.
    """
    limit = 50
    offset = (page - 1) * limit
    
    logs = await get_audit_logs(
        limit=limit,
        offset=offset,
        user_id=user_filter,
        auditable_type=type_filter,
        action=action_filter
    )
    
    # Count total manually
    async with engine.connect() as conn:
        count_query = "SELECT COUNT(*) as total FROM audit_logs WHERE 1=1"
        count_params = {}
        
        if user_filter:
            count_query += " AND user_id = :user_id"
            count_params["user_id"] = user_filter
        
        if type_filter:
            count_query += " AND auditable_type = :auditable_type"
            count_params["auditable_type"] = type_filter
        
        if action_filter:
            count_query += " AND action = :action"
            count_params["action"] = action_filter
        
        count_result = await conn.execute(text(count_query), count_params)
        total = count_result.scalar() or 0
    
    for log in logs:
        if log.get("created_at"):
            log["created_at_formatted"] = log["created_at"].strftime("%d/%m/%Y %H:%M:%S")
    
    total_pages = (total + limit - 1) // limit
    
    return templates.TemplateResponse(
        request,
        "admin/audit_logs.html",
        {
            "request": request,
            "user_id": admin_id,
            "logs": logs,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "user_filter": user_filter,
            "action_filter": action_filter,
            "type_filter": type_filter,
            "actions": ["create", "update", "delete", "login"],
            "types": ["user", "event", "order", "ticket"]
        }
    )
 
# ===== USERS =====
 
@router.get("/users", response_class=HTMLResponse)
async def get_users_dashboard(
    request: Request,
    admin_id: int = Depends(verify_admin),
    page: int = 1
):
    """
    Manage users dashboard (view + edit).
    """
    limit = 50
    offset = (page - 1) * limit
    
    async with engine.connect() as conn:
        count_result = await conn.execute(text("SELECT COUNT(*) as total FROM users"))
        total = count_result.scalar() or 0
        
        query = "SELECT id, name, email, phone_number, is_admin, created_at FROM users ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        result = await conn.execute(text(query), {"limit": limit, "offset": offset})
        users = [dict(row) for row in result.mappings()]
    
    total_pages = (total + limit - 1) // limit
    
    for user in users:
        if user.get("created_at"):
            user["created_at_formatted"] = user["created_at"].strftime("%d/%m/%Y %H:%M")
    
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {
            "request": request,
            "user_id": admin_id,
            "users": users,
            "total": total,
            "page": page,
            "total_pages": total_pages
        }
    )
 
# ===== EDIT USER =====
 
@router.get("/users/{user_id_target}", response_class=HTMLResponse)
async def get_user_edit_page(
    request: Request,
    user_id_target: int,
    admin_id: int = Depends(verify_admin)
):
    """
    Admin page to view/edit/delete a specific user.
    """
    user = await get_user_by_id(user_id_target)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return templates.TemplateResponse(
        request,
        "admin/user_detail.html",
        {
            "request": request,
            "user_id": admin_id,
            "user": user
        }
    )
 
@router.post("/users/{user_id_target}", response_class=HTMLResponse)
async def post_user_edit(
    request: Request,
    user_id_target: int,
    admin_id: int = Depends(verify_admin),
    name: Annotated[str, Form()] | None = None
):
    """
    Update user information (admin).
    """
    user = await get_user_by_id(user_id_target)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get form data
    form_data = await request.form()
    
    # Connect to database
    async with engine.connect() as conn:
        # Prepare update dict
        updates = []
        params = {"user_id": user_id_target}
        
        if name:
            updates.append("name = :name")
            params["name"] = name
        
        # Checkbox is_admin
        is_admin = "is_admin" in form_data
        updates.append("is_admin = :is_admin")
        params["is_admin"] = is_admin
        
        # Execute update
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = :user_id"
        await conn.execute(text(query), params)
        await conn.commit()
    
    # Convert datetime to string before log
    old_values_audit = {"name": user.get("name"), "is_admin": user.get("is_admin")}
    new_values_audit = {"name": name, "is_admin": is_admin}
    
    # Log action
    await log_action(
        action="update",
        auditable_type="user",
        auditable_id=user_id_target,
        user_id=admin_id,
        old_values=old_values_audit,
        new_values=new_values_audit,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    request.session["flash"] = "Usuário atualizado com sucesso!"
    return RedirectResponse(url=f"/admin/users/{user_id_target}", status_code=303)
 
# ===== DELETE USER =====
 
@router.post("/users/{user_id_target}/delete", response_class=HTMLResponse)
async def delete_user_route(
    request: Request,
    user_id_target: int,
    admin_id: int = Depends(verify_admin)
):
    """
    Delete a user (admin only).
    """
    user = await get_user_by_id(user_id_target)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_id_target == admin_id:
        raise HTTPException(status_code=400, detail="Você não pode deletar sua própria conta")
    
    # Check if user has orders
    async with engine.connect() as conn:
        order_check = await conn.execute(
            text("SELECT COUNT(*) as total FROM orders WHERE buyer_id = :user_id"),
            {"user_id": user_id_target}
        )
        order_count = order_check.scalar() or 0
    
    if order_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Não é possível deletar este usuário. Ele possui {order_count} ordem(s) associada(s)."
        )
    
    # Delete user
    async with engine.connect() as conn:
        await conn.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id_target})
        await conn.commit()
    
    #  Convert dict with datetime to dict with strings
    old_values_audit = dict(user)
    # Convert all datetime to string
    for key, value in old_values_audit.items():
        if hasattr(value, 'isoformat'):  # If it is datetime
            old_values_audit[key] = value.isoformat()
    
    # Log action
    await log_action(
        action="delete",
        auditable_type="user",
        auditable_id=user_id_target,
        user_id=admin_id,
        old_values=old_values_audit,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    request.session["flash"] = "Usuário deletado com sucesso!"
    return RedirectResponse(url="/admin/users", status_code=303)
 
# ===== EVENTS =====
 
@router.get("/events", response_class=HTMLResponse)
async def get_events_dashboard(
    request: Request,
    admin_id: int = Depends(verify_admin),
    page: int = 1
):
    """
    Manage events dashboard (view + edit).
    """
    limit = 50
    offset = (page - 1) * limit
    
    async with engine.connect() as conn:
        count_result = await conn.execute(text("SELECT COUNT(*) as total FROM events"))
        total = count_result.scalar() or 0
        
        query = """
        SELECT id, title, organizer_id, state, city, total_capacity, 
               start_date, end_date, category, created_at 
        FROM events 
        ORDER BY start_date DESC 
        LIMIT :limit OFFSET :offset
        """
        result = await conn.execute(text(query), {"limit": limit, "offset": offset})
        events = [dict(row) for row in result.mappings()]
    
    total_pages = (total + limit - 1) // limit
    
    for event in events:
        if event.get("created_at"):
            event["created_at_formatted"] = event["created_at"].strftime("%d/%m/%Y %H:%M")
        if event.get("start_date"):
            event["start_date_formatted"] = event["start_date"].strftime("%d/%m/%Y %H:%M")
    
    return templates.TemplateResponse(
        request,
        "admin/events.html",
        {
            "request": request,
            "user_id": admin_id,
            "events": events,
            "total": total,
            "page": page,
            "total_pages": total_pages
        }
    )
 
# ===== DELETE EVENT (ADMIN) =====
 
@router.post("/{event_id}/admin-delete", response_class=HTMLResponse)
async def admin_delete_event(
    request: Request,
    event_id: int,
    user_id: int = Depends(verify_user_token)
):
    """
    Delete an event (admin only) - BYPASS owner check.
    """
    # Get event
    async with engine.connect() as conn:
        event_query = await conn.execute(
            text("SELECT * FROM events WHERE id = :event_id"),
            {"event_id": event_id}
        )
        event = event_query.mappings().one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if user is admin
    user = await get_user_by_id(user_id)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access Denied: Admin only")
    
    # Connect to database
    try:
        # DELETE event
        async with engine.connect() as conn:
            await conn.execute(text("DELETE FROM events WHERE id = :event_id"), {"event_id": event_id})
            await conn.commit()
        
        # Convert dict with datetime to dict with strings
        old_values_audit = dict(event)
        # Convert all datetime to string
        for key, value in old_values_audit.items():
            if hasattr(value, 'isoformat'):  # If it is datetime
                old_values_audit[key] = value.isoformat()
        
        # Log action
        await log_action(
            action="delete",
            auditable_type="event",
            auditable_id=event_id,
            user_id=user_id,
            old_values=old_values_audit,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        request.session["flash"] = "Evento deletado com sucesso!"
        request.session["flash_type"] = "success"
        return RedirectResponse(url="/events", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao deletar evento: {str(e)}")
 
# ===== ORDERS (View Only) =====
 
@router.get("/orders", response_class=HTMLResponse)
async def get_orders_dashboard(
    request: Request,
    admin_id: int = Depends(verify_admin),
    page: int = 1
):
    """
    View all orders dashboard (read-only).
    """
    limit = 50
    offset = (page - 1) * limit
    
    async with engine.connect() as conn:
        count_result = await conn.execute(text("SELECT COUNT(*) as total FROM orders"))
        total = count_result.scalar() or 0
        
        query = """
        SELECT o.*, u.name as buyer_name, u.email as buyer_email, e.title as event_title
        FROM orders o
        LEFT JOIN users u ON o.buyer_id = u.id
        LEFT JOIN events e ON o.event_id = e.id
        ORDER BY o.created_at DESC
        LIMIT :limit OFFSET :offset
        """
        result = await conn.execute(text(query), {"limit": limit, "offset": offset})
        orders = [dict(row) for row in result.mappings()]
    
    total_pages = (total + limit - 1) // limit
    
    for order in orders:
        if order.get("created_at"):
            order["created_at_formatted"] = order["created_at"].strftime("%d/%m/%Y %H:%M")
    
    return templates.TemplateResponse(
        request,
        "admin/orders.html",
        {
            "request": request,
            "user_id": admin_id,
            "orders": orders,
            "total": total,
            "page": page,
            "total_pages": total_pages
        }
    )
 
# ===== TICKETS (View Only) =====
 
@router.get("/tickets", response_class=HTMLResponse)
async def get_tickets_dashboard(
    request: Request,
    admin_id: int = Depends(verify_admin),
    page: int = 1
):
    """
    View all tickets dashboard (read-only).
    """
    limit = 50
    offset = (page - 1) * limit
    
    async with engine.connect() as conn:
        count_result = await conn.execute(text("SELECT COUNT(*) as total FROM tickets"))
        total = count_result.scalar() or 0
        
        query = """
        SELECT t.*, o.buyer_id, o.id as order_id, u.name as buyer_name, u.email as buyer_email
        FROM tickets t
        LEFT JOIN orders o ON t.order_id = o.id
        LEFT JOIN users u ON o.buyer_id = u.id
        ORDER BY t.created_at DESC
        LIMIT :limit OFFSET :offset
        """
        result = await conn.execute(text(query), {"limit": limit, "offset": offset})
        tickets = [dict(row) for row in result.mappings()]
    
    total_pages = (total + limit - 1) // limit
    
    for ticket in tickets:
        if ticket.get("created_at"):
            ticket["created_at_formatted"] = ticket["created_at"].strftime("%d/%m/%Y %H:%M")
        if ticket.get("used_at"):
            ticket["used_at_formatted"] = ticket["used_at"].strftime("%d/%m/%Y %H:%M")
    
    return templates.TemplateResponse(
        request,
        "admin/tickets.html",
        {
            "request": request,
            "user_id": admin_id,
            "tickets": tickets,
            "total": total,
            "page": page,
            "total_pages": total_pages
        }
    )