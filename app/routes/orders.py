"""
Orders routes for TicketPlus.
"""

from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings, templates
from app.middleware.rate_limiter import limiter
from app.services.audit_service import (
    get_ip_from_request,
    get_user_agent_from_request,
    log_action,
    prepare_old_new_values,
)
from app.services.auth_service import verify_user_token
from app.services.order_service import (
    calculate_order_total,
    cancel_order,
    create_order,
    get_order_by_id,
    get_orders_by_buyer,
    get_ticket_type_with_event,
    process_successful_payment,
    validate_ticket_availability,
)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Configure router
router = APIRouter(prefix="/checkout", tags=["orders"])

# ==========================================
# PAYMENT SUCCESS ROUTE
# ==========================================

@router.get("/success", response_class=HTMLResponse)
async def payment_success(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Render success page after payment (requires login).
    """
    # Get order_id from session
    target_order_id = request.session["order_id"]

    # Se não encontrar o pedido na sessão ou na URL, lança 404
    if not target_order_id:
        raise HTTPException(
            status_code=404, 
            detail="Not Found: Nenhum pedido encontrado na sessão ou na URL. Fluxo inválido."
        )

    # Busca as informações do pedido
    order = await get_order_by_id(target_order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Not Found: Pedido não encontrado ou não existe.")

    # Fallback para ambiente local: se o pagamento ainda estiver pendente (webhook não chegou),
    # força o processamento do pagamento para gerar o pedido como pago
    if order["payment_status"] == "pending":
        await process_successful_payment(target_order_id, order.get("stripe_payment_id") or "manual_local_dev")

    # Redireciona o comprador para a tela de coleta de dados dos ingressos (onde os registros são gerados no DB)
    return RedirectResponse(url=f"/tickets/collect/{target_order_id}", status_code=303)

# ==========================================
# ORDER HISTORY ROUTES
# ==========================================

@router.get("/history", response_class=HTMLResponse)
async def order_history(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Render user's order history (requires login).
    """
    # Fetch all orders made by the current user
    orders = await get_orders_by_buyer(user_id)

    # Return all orders info to be rendered in order_history.html
    return templates.TemplateResponse(
        request,
        "order_history.html",
        {
            "request": request,
            "orders": orders,
            "user_id": user_id
        }
    )

# ==========================================
# PAYMENT CANCEL ROUTE
# ==========================================

@router.get("/cancel", response_class=HTMLResponse)
async def payment_cancel(
    request: Request,
    user_id: int = Depends(verify_user_token)
):
    """
    Handle cancelled payment (requires login).
    """
    # Get order_id from session
    order_id = request.session["order_id"]

    # If order_id not found in the user's session, return 404
    if not order_id:
        raise HTTPException(status_code=404, detail="Not Found: Nenhum pedido encontrado na sessão. Fluxo inválido.")

    # Cancel order
    cancelled_order = await cancel_order(order_id)

    # Display a message based on if the order was cancelled or not
    if cancelled_order:
        request.session["flash"] = "Pagamento cancelado."
    else:
        request.session["flash"] = "Um erro ocorreu enquanto cancelávamos seu pedido. Por favor, tente novamente agora ou mais tarde."

    # Redirect to events main page
    return templates.TemplateResponse(
        request,
        "cancel.html",
        {
            "request": request,
            "user_id": user_id
        }
    )

# ==========================================
# STRIPE WEBHOOK
# ==========================================

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events (payment_intent.succeeded).
    """
    # Get payload and signature
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Construct payload
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad Request: Payload inválido.")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Bad Request: Assinatura inválida.")

    # Treats only the event that was successful
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"].to_dict()

        stripe_payment_id = payment_intent.get("id")

        metadata = payment_intent.get("metadata", {})
        raw_order_id = metadata.get("order_id")

        if not raw_order_id:
            print("X Error: order_id not found inside Stripe metadata.")
            return {"status": "missing metadata"}

        order_id = int(raw_order_id)

        try:
            await process_successful_payment(order_id, stripe_payment_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        # ==== AUDIT LOGS ENTRY ====
        # Fetch order to get buyer_id
        order = await get_order_by_id(order_id)
        buyer_id = order["buyer_id"] if order else None

        # Fetch old order and payment status
        old_dict = {
            "payment_status": 'pending',
            "order_status": 'pending'
        }
    
        # Fetch new order and payment status
        new_dict = {
            "payment_status": 'paid',
            "order_status": 'confirmed'
        }
    
        # Convert from dict to JSON string
        old_values_json, new_values_json = prepare_old_new_values(old_dict, new_dict)
    
        # Log action
        try:
            await log_action(
                action='update',
                auditable_type='order',
                auditable_id=order_id,
                user_id=buyer_id,
                old_values=old_values_json,
                new_values=new_values_json,
                ip_address=None,
                user_agent=None
            )
        except ValueError:
            pass
        # ==== END OF AUDIT LOGS ENTRY ====

    # If everything went well, return success
    return {"status": "success"}

# ==========================================
# CHECKOUT ROUTES
# ==========================================

@router.get("/{ticket_type_id}", response_class=HTMLResponse)
async def get_checkout_page(
    request: Request,
    ticket_type_id: int,
    user_id: int = Depends(verify_user_token)
):
    """
    Render checkout page for a specific ticket type (requires login).
    """
    # Fetch ticket type with respective event info
    tt_event_info = await get_ticket_type_with_event(ticket_type_id)

    # If it doesn't exist, return 404
    if not tt_event_info:
        raise HTTPException(status_code=404, detail="Not Found: Evento e lotes respectivos não encontrados ou não existe.")

    # Separate event info from ticket type info
    event_info = {"organizer_id": tt_event_info["organizer_id"], "start_date": tt_event_info["start_date"]}

    # Return info to be rendered in checkout.html
    return templates.TemplateResponse(
        request,
        "checkout.html",
        {
            "request": request,
            "ticket_type": tt_event_info,
            "event": event_info,
            "user_id": user_id,
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY
        }
    )


@router.post("/{ticket_type_id}", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def post_checkout(
    request: Request,
    ticket_type_id: int,
    user_id: int = Depends(verify_user_token),
    quantity: Annotated[int, Form(gt=0)] = 1
):
    """
    Create an order and Stripe PaymentIntent (requires login).
    """
    # Validate ticket availability
    availability = await validate_ticket_availability(ticket_type_id, quantity)

    if not availability:
        raise HTTPException(status_code=400, detail="Bad Request: Não há ingressos disponíveis.")
    
    # Get ticket type + respective event info
    event = await get_ticket_type_with_event(ticket_type_id)

    # Calculate total amount to be paid
    total_amount = await calculate_order_total(ticket_type_id, quantity)

    if total_amount is None:
        raise HTTPException(status_code=400, detail="Lote de ingressos inválido ou preço não encontrado.")

    # Create order in the database
    order_id = await create_order(
        user_id, 
        event["event_id"], 
        ticket_type_id,
        quantity,
        total_amount
    )

    # ==== AUDIT LOGS ENTRY ====
    # Fetch order data
    new_values = {
        "event_id": event["event_id"],
        "ticket_type_id": ticket_type_id,
        "quantity": quantity,
        "total_amount": total_amount,
        "payment_status": 'pending',
        "order_status": 'pending'
    }

    # Convert from dict to JSON string
    _ , new_values_json = prepare_old_new_values(None, new_values)

    # Log action
    try:
        await log_action(
            action='create',
            auditable_type='order',
            auditable_id=order_id,
            user_id=user_id,
            old_values=None,
            new_values=new_values_json,
            ip_address=get_ip_from_request(request),
            user_agent=get_user_agent_from_request(request)
        )
    except ValueError:
        pass
    # ==== END OF AUDIT LOGS ENTRY ====

    # Create a Stripe Payment Intent
    try:
        intent = stripe.PaymentIntent.create(
            amount=total_amount,
            currency="brl",
            metadata={"order_id": order_id}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    
    # Flash message
    request.session["flash"] = "Processando pagamento.. Por favor, espere o próximo passo."
    request.session["order_id"] = order_id

    # Return all necessary info to render payment_form.html
    return templates.TemplateResponse(
        request,
        "payment_form.html",
        {
            "request": request,
            "order_id": order_id,
            "client_secret": intent.client_secret,
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "total_amount": total_amount,
            "quantity": quantity,
            "user_id": user_id
        }
    )