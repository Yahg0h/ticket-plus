"""
All services related to user management used across all TicketPlus routes.
"""

from sqlalchemy import text

from app.database import engine
from app.services.auth_service import hash_password

# ==========================================
# DATABASE OPERATIONS
# ==========================================


async def check_email_exists(email: str, exclude_user_id: int | None = None) -> bool:
    """
    Check if an email is already registered.
    
    Args:
        email: Email to check
        exclude_user_id: User ID to exclude from check (for updates)
    
    Returns:
        bool: True if email exists, False otherwise
    """
    # Connect to database
    async with engine.connect() as conn:
        # If exclude_user_id is None, don't add 'AND' parameter
        if exclude_user_id:
            query = await conn.execute(
                text("SELECT * FROM users WHERE email = :email AND id != :id"), 
                {"email": email, "id": exclude_user_id}
            )
        else:
            query = await conn.execute(
                text("SELECT * FROM users WHERE email = :email"), 
                {"email": email}
            )
        existing_email = query.mappings().first()

        # If the email is already registered, return True
        if existing_email:
            return True

        # Else, return False
        return existing_email


async def check_phone_exists(phone_number: str, exclude_user_id: int | None = None) -> bool:
    """
    Check if a phone number is already registered.
    
    Args:
        phone_number: Phone number to check
        exclude_user_id: User ID to exclude from check
    
    Returns:
        bool: True if phone exists, False otherwise
    """
    async with engine.connect() as conn:
        # If exclude_user_id is None, don't add 'AND' parameter
        if exclude_user_id:
            query = await conn.execute(
                text("SELECT * FROM users WHERE phone_number = :phone_number AND id != :id"), 
                {"phone_number": phone_number, "id": exclude_user_id}
            )
        else:
            query = await conn.execute(
                text("SELECT * FROM users WHERE phone_number = :phone_number"), 
                {"phone_number": phone_number}
            )
        existing_phone = query.mappings().first()

        # If phone number is already registered, return True
        if existing_phone:
            return True

        # Else, return False
        return existing_phone


async def update_user(
    user_id: int,
    name: str | None = None,
    email: str | None = None,
    phone_number: str | None = None,
    state: str | None = None,
    city: str | None = None,
    password: str | None = None
) -> bool:
    """
    Update user data in the database.
    
    Args:
        user_id: User ID
        name: New name (optional)
        email: New email (optional)
        phone_number: New phone (optional)
        state: New state (optional)
        city: New city (optional)
        password: New password (optional, will be hashed)
    
    Returns:
        bool: True if update successful
    
    Raises:
        ValueError: If email or phone already exists
    """
    async with engine.connect() as conn:

        # Build dynamic query where only the settings which were chosen to be changed get updated
        updates = []
        params = {"user_id": user_id}

        if name:
            updates.append("name = :name")
            params["name"] = name

        if email:
            # If a new email is to be registered, check if the email is already registered
            existing_email = await check_email_exists(email, user_id)

            # If it is registered, return error
            if existing_email:
                raise ValueError

            # Else, update
            updates.append("email = :email")
            params["email"] = email

        if phone_number:
            # If a new phone number is to be registered, check if the email is already registered
            existing_phone = await check_phone_exists(phone_number, user_id)

            if existing_phone:
                raise ValueError

            updates.append("phone_number = :phone_number")
            params["phone_number"] = phone_number

        if password:
            # If a new password is added, hash it first
            password = hash_password(password)

            updates.append("password_hash = :password_hash")
            params["password_hash"] = password

        if state:
            updates.append("state = :state")
            params["state"] = state

        if city:
            updates.append("city = :city")
            params["city"] = city

        if not updates:
            # If there wan't any updates, just return True for what's current registered
            return True

        query = f"UPDATE users SET {', '.join(updates)} WHERE id = :user_id"

        # UPDATE new information into the database
        await conn.execute(text(query), params)
        await conn.commit()

        # Return success
        return True


async def delete_user(user_id: int) -> bool:
    """
    Delete a user from the database (hard delete).
    
    Note: Currently, this function performs a hard delete, as intentionally designed for this project.
    For a soft delete, changes to core structure will need to be made by you.
    
    Args:
        user_id: User ID to delete
    
    Returns:
        bool: True if deletion successful
    """
    async with engine.connect() as conn:
        await conn.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
        await conn.commit()

        return True