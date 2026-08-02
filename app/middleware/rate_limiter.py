# Rate limiting configuration for TicketPlus

from slowapi import Limiter
from slowapi.util import get_remote_address

# Configure limiter
limiter = Limiter(key_func=get_remote_address)