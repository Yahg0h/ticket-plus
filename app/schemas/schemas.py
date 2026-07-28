from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

# ==========================================
# 1. Regex Constants (Validations)
# ==========================================
# Accepts formated CPF (000.000.000-00) or numbers only (00000000000)
CPF_REGEX = r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$"

# Accepts formated Brazilian phone numbers (with or without DDD, with or without +55)
# Ex: (11) 99999-9999, 11999999999, +5511999999999
PHONE_REGEX = r"^(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4})-?\d{4}$"

# Accepts IPv4 and IPv6
IP_REGEX = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"


# ==========================================
# 2. ENUMS
# ==========================================
class EventCategory(str, Enum):
    ENTERTAINMENT = "entertainment"
    CORPORATE = "corporate"
    ACADEMIC = "academic"
    SOCIAL = "social"
    SPORTS = "sports"
    MARKETING = "marketing"
    WORKSHOP = "workshop"
    OTHER = "other"


class TicketType(str, Enum):
    STANDARD = "standard"
    VIP = "vip"
    EARLY_BIRD = "early_bird"
    GROUP = "group"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class TicketStatus(str, Enum):
    VALID = "valid"
    USED = "used"
    CANCELLED = "cancelled"


# ==========================================
# 3. USER SCHEMAS
# ==========================================
class UserBase(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, pattern=PHONE_REGEX, max_length=20)
    cpf: str = Field(..., pattern=CPF_REGEX, max_length=14)
    state: str = Field(..., max_length=255)
    city: str = Field(..., max_length=255)

    @model_validator(mode="after")
    def validate_contact(self) -> "UserBase":
        if not self.email and not self.phone_number:
            raise ValueError("The user must provide at least one email address or phone number.")
        return self


class UserCreate(UserBase):
    """Scheme to create a user (POST)"""
    password: str = Field(..., min_length=6, max_length=255)


class UserLogin(BaseModel):
    """Schema to authenticate a user during login"""
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, pattern=PHONE_REGEX, max_length=20)
    password: str

    @model_validator(mode="after")
    def validate_contact(self) -> "UserLogin":
        if not self.email and not self.phone_number:
            raise ValueError("Must provide either an email or a phone number to log in.")
        return self


class UserUpdate(BaseModel):
    """Schema for updating user data (PUT)"""
    name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, pattern=PHONE_REGEX, max_length=20)
    state: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=6, max_length=255)

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """Schema for returning user data (GET)"""
    id: int
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. EVENT SCHEMAS
# ==========================================
class EventBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    banner_url: str | None = Field(default=None, max_length=255)
    category: EventCategory
    state: str = Field(..., max_length=255)
    city: str = Field(..., max_length=255)
    address: str = Field(..., max_length=255)
    total_capacity: int = Field(..., gt=0)
    start_date: datetime
    end_date: datetime


class EventCreate(EventBase):
    """Schema for registering an event (POST)"""
    organizer_id: int


class EventUpdate(BaseModel):
    """Schema for updating event data (PUT)"""
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    banner_url: str | None = Field(default=None, max_length=255)
    category: EventCategory | None = None
    state: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    total_capacity: int | None = Field(default=None, gt=0)
    available_tickets: int | None = Field(default=None, ge=0)
    start_date: datetime | None = None
    end_date: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EventResponse(EventBase):
    """Schema for returning a event data (GET)"""
    id: int
    organizer_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 5. TICKET TYPE SCHEMAS (ticket Batch)
# ==========================================
class TicketTypeBase(BaseModel):
    type: TicketType
    price: int = Field(..., ge=0, description="Price in cents (e.g., 10000 = R$ 100,00)")
    quantity_available: int = Field(..., ge=0)


class TicketTypeCreate(TicketTypeBase):
    """Schema for registering an event ticket type"""
    event_id: int


class TicketTypeUpdate(BaseModel):
    """Schema to update ticket type details (e.g., price adjustment)"""
    type: TicketType | None = None
    price: int | None = Field(default=None, ge=0, description="Price in cents")

    model_config = ConfigDict(from_attributes=True)


class TicketTypeResponse(TicketTypeBase):
    """Schema for returning batch data"""
    id: int
    event_id: int
    quantity_sold: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 6. ORDER SCHEMAS
# ==========================================
class OrderBase(BaseModel):
    event_id: int
    total_amount: int = Field(..., ge=0, description="Sum of values in cents")


class OrderCreate(OrderBase):
    """Schema to initiate a checkout request (POST)"""
    buyer_id: int
    idempotency_key: str = Field(..., max_length=255)


class OrderUpdate(BaseModel):
    """Schema for updating payment/order status"""
    payment_status: PaymentStatus | None = None
    order_status: OrderStatus | None = None
    stripe_payment_id: str | None = Field(default=None, max_length=255)
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(OrderBase):
    """Schema for returning the order summary (GET)"""
    id: int
    buyer_id: int
    payment_status: PaymentStatus
    stripe_payment_id: str | None = None
    idempotency_key: str
    order_status: OrderStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 7. TICKET SCHEMAS (Tickets Issued)
# ==========================================
class TicketBase(BaseModel):
    holder_name: str = Field(..., max_length=255)
    holder_cpf: str = Field(..., pattern=CPF_REGEX, max_length=14)


class TicketCreate(TicketBase):
    """Schema for generating a personalized ticket linked to an order"""
    order_id: int
    ticket_type_id: int
    price_paid: int = Field(..., ge=0)


class TicketUpdate(BaseModel):
    """Schema for listing the user's tickets (GET /meus-ingressos)"""
    holder_name: str | None = Field(default=None, max_length=255)
    holder_cpf: str | None = Field(default=None, pattern=CPF_REGEX, max_length=14)
    status: TicketStatus | None = None

    model_config = ConfigDict(from_attributes=True)


class TicketResponse(TicketBase):
    """Schema for listing the user's tickets (GET /meus-ingressos)"""
    id: int
    order_id: int
    ticket_type_id: int
    price_paid: int
    status: TicketStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 8. AUDIT LOG SCHEMAS
# ==========================================
class AuditLogBase(BaseModel):
    action: str = Field(..., max_length=50)
    auditable_type: str = Field(..., max_length=50)
    auditable_id: int
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    ip_address: str | None = Field(default=None, pattern=IP_REGEX, max_length=45)
    user_agent: str | None = Field(default=None, max_length=255)


class AuditLogCreate(AuditLogBase):
    """Schema for recording an audit event"""
    user_id: int | None = None


class AuditLogResponse(AuditLogBase):
    """Schema for reading the audit log"""
    id: int
    user_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)