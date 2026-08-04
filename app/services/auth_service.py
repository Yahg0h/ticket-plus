"""
All services related to authentication used across all TicketPlus routes.
"""

import json
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy import text

from app.config import settings
from app.database import engine

# ==========================================
# PASSWORD HASHING
# ==========================================

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hash a plain password using Argon2.
    """
    hashed_pass = pwd_context.hash(password)
    return hashed_pass


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plain password against its hash.
    """
    verify_pass = pwd_context.verify(password, hashed)
    return verify_pass

# ==========================================
# JWT TOKEN MANAGEMENT
# ==========================================

def create_jwt_token(user_id: int) -> str:
    """
    Create a JWT token with expiration.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.TOKEN_EXPIRATION_MINS)
    payload = {
        "sub": str(user_id),
        "exp": expire
    }
    token = jwt.encode(payload, settings.JWT_SECRET, settings.ALGORITHM)
    return token


def decode_token(token: str, ignore_exp: bool = False) -> int:
    """
    Decode a JWT token and return user_id.
    """
    try:
        # If ignore_exp=True, then ignore the expiration date
        options = {"verify_exp": not ignore_exp}
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM], options=options)
        user_id = payload.get("sub")
        # If there isn't a valid user_id in the token, return error
        if not user_id:
            raise ValueError("Token inválido: no user_id")
        # Else, return the user_id
        return int(user_id)
    except Exception as e:
        raise ValueError(f"Decodificação de token falhou: {str(e)}")

async def verify_user_token(request: Request) -> int:
    """
    Mandatory dependency (for routes that require login)
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized: Não logado.")
    
    try:
        user_id = decode_token(token, ignore_exp=False)
        return user_id
    except ValueError:
        raise HTTPException(status_code=401, detail="Unauthorized: Token inválido.")

async def get_current_user_optional(request: Request) -> int | None:
    """
    Optional dependency (for routes that can have a user logged in or not)
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        user_id = decode_token(token, ignore_exp=False)
        return user_id
    except ValueError:
        return None

# ==========================================
# LOCATION VALIDATION
# ==========================================

def load_brazil_data() -> dict:
    """
    Load estados and cidades from brazil-states-cities.json.

    Returns:
        dict: Loaded JSON data
    """
    with open('app/static/brazil-states-cities.json', 'r', encoding='utf-8') as f:
        return json.load(f)


async def validate_location(state_code: str, city_name: str) -> bool:
    """
    Validate state and city against brazil-states-cities.json data.
    """
    try:
        # Load locations file
        brazil_locations = load_brazil_data()

        # Access BR -> states -> state_code -> (all for validation checking)
        br_data = brazil_locations.get('BR', {})
        states = br_data.get('states', {})
        state = states.get(state_code)
        if not state:
            return False

        cities = state.get('cities', [])
        return city_name in cities
    except Exception:
        return False

# ==========================================
# DATABASE OPERATIONS
# ==========================================

async def get_user_by_email(email: str) -> dict | None:
    """
    Fetch a user by email from the database.
    
    Args:
        email: User email
    
    Returns:
        dict or None: User data or None if not found
    """
    # Connect to database
    async with engine.connect() as conn:
        # Search DB for the user
        query = await conn.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
        existing_user = query.mappings().one_or_none() # Convert from row to dict

        return existing_user # The receiving route will decide what to do in case of None or data checking


async def get_user_by_phone(phone_number: str) -> dict | None:
    """
    Fetch a user by phone_number from the database.
    
    Args:
        phone_number: User phone number
    
    Returns:
        dict or None: User data or None if not found
    """
    async with engine.connect() as conn:
        query = await conn.execute(text("SELECT * FROM users WHERE phone_number = :phone_number"), {"phone_number": phone_number})
        existing_user = query.mappings().one_or_none()

        return existing_user


async def get_user_by_id(user_id: int) -> dict | None:
    """
    Fetch a user's info by their ID from the database.
    
    Args:
        user_id: User ID
    
    Returns:
        dict or None: User data or None if not found
    """
    async with engine.connect() as conn:
        query = await conn.execute(text("SELECT * FROM users WHERE id = :user_id"), {"user_id": user_id})
        existing_user = query.mappings().one_or_none()

        return existing_user


async def create_user(
    name: str,
    email: str | None,
    phone_number: str | None,
    password: str,
    cpf: str,
    state: str,
    city: str
) -> int:
    """
    Insert a new user into the database.
    
    Args:
        name: User name
        email: User email (optional)
        phone_number: User phone (optional)
        password: Plain password to hash
        cpf: User CPF
        state: User state
        city: User city
    
    Returns:
        int: The newly created user's ID
    
    Raises:
        ValueError: If email or phone already exists (catch DB exception)
    """
    # Hash user's password for security
    hashed_pass = hash_password(password)

    # Connect to database
    async with engine.connect() as conn:
        # Search for a already existing user with the same email and/or phone number
        # Build dyanmic query
        conditions = []
        params = {}

        email = email if email else None
        phone_number = phone_number if phone_number else None
        
        if email:
            conditions.append("email = :email")
            params["email"] = email
        
        if phone_number:
            conditions.append("phone_number = :phone_number")
            params["phone_number"] = phone_number
        
        # If there is any condition, execute the query
        if conditions:
            query_str = "SELECT * FROM users WHERE " + " OR ".join(conditions)
            contact_query = await conn.execute(text(query_str), params)
            existing_contact = contact_query.mappings().first()
        else:
            existing_contact = None

        # If it exists, raise error
        if existing_contact:
            raise ValueError

        # INSERT query
        query = """
        INSERT INTO users (name, email, phone_number, password_hash, cpf, state, city)
        VALUES (:name, :email, :phone_number, :password_hash, :cpf, :state, :city)
        """
        # INSERT user in the DB
        await conn.execute(text(query), {"name": name, "email": email, "phone_number": phone_number, "password_hash": hashed_pass, "cpf": cpf, "state": state, "city": city})
        await conn.commit()

        # Fetch the id of the recently added user, and return it
        result = await conn.execute(text("SELECT id FROM users WHERE id = LAST_INSERT_ID()"))
        query_id = result.scalar() # Converts from row to int
        return query_id



async def authenticate_user(email: str | None, phone_number: str | None, password: str) -> dict | None:
    """
    Authenticate a user by email/phone and password.
    
    Args:
        email: User email (optional)
        phone_number: User phone (optional)
        password: Plain password to verify
    
    Returns:
        dict or None: User data if authentication successful, None otherwise
    """
    # Get user information by their email or phone_number
    if email:
        user = await get_user_by_email(email)
    elif phone_number:
        user = await get_user_by_phone(phone_number)

    # If the user doesn't exist, return none
    if not user:
        return None
    # Check if the passwords don't match, return None if it does
    if not verify_password(password, user["password_hash"]):
        return None

    # Return user info dict
    return user
        