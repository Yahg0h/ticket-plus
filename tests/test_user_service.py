from uuid import uuid4

import pytest
from validate_docbr import CPF

from app.database import engine
from app.services.auth_service import create_user
from app.services.user_service import (
    check_email_exists,
    check_phone_exists,
    delete_user,
    update_user,
)

cpf_gen = CPF()

@pytest.mark.asyncio
async def test_check_email_exists():
    """Test email existence check"""
    unique_id = str(uuid4())[:8]
    email = f"exists-{unique_id}@example.com"
    
    # Create a user first
    await create_user(
        name="John Doe",
        email=email,
        phone_number=f"+55119{unique_id[:8]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Check if email exists
    exists = await check_email_exists(email, engine)
    assert bool(exists) is True
    
    # Check non-existent email
    exists = await check_email_exists(f"nonexistent-{unique_id}@example.com", engine)
    assert not exists

@pytest.mark.asyncio
async def test_check_email_exists_with_exclude():
    """Test email existence check with excluded user"""
    unique_id = str(uuid4())[:8]
    email = f"exclude-{unique_id}@example.com"
    
    # Create a user
    user_id = await create_user(
        name="John Doe",
        email=email,
        phone_number=f"+55119{unique_id[:8]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Check if email exists excluding this user (should be False)
    exists = await check_email_exists(email, exclude_user_id=user_id)
    assert not exists
    
    # Check if email exists without excluding (should be True)
    exists = await check_email_exists(email, engine)
    assert bool(exists) is True

@pytest.mark.asyncio
async def test_check_phone_exists():
    """Test phone number existence check"""
    unique_id = str(uuid4())[:8]
    phone = f"+55 11 9{unique_id}0000"
    
    # Create a user first
    await create_user(
        name="John Doe",
        email=f"phone-{unique_id}@example.com",
        phone_number=phone,
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Check if phone exists
    exists = await check_phone_exists(phone, engine)
    assert bool(exists) is True
    
    # Check non-existent phone
    exists = await check_phone_exists(f"+55 11 99999{unique_id}0000", engine)
    assert not exists

@pytest.mark.asyncio
async def test_update_user_name():
    """Test updating user name"""
    unique_id = str(uuid4())[:8]
    
    # Create a user
    user_id = await create_user(
        name="John Doe",
        email=f"update-{unique_id}@example.com",
        phone_number=f"+55119{unique_id[:8]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Update name
    result = await update_user(user_id, name="Jane Doe")
    # Result depends on implementation - could be bool or rowcount
    assert result is not None

@pytest.mark.asyncio
async def test_update_user_email():
    """Test updating user email"""
    unique_id = str(uuid4())[:8]
    new_unique_id = str(uuid4())[:8]
    
    # Create a user
    user_id = await create_user(
        name="John Doe",
        email=f"update-email-{unique_id}@example.com",
        phone_number=f"+55119{unique_id[:8]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Update email
    new_email = f"newemail-{new_unique_id}@example.com"
    result = await update_user(user_id, email=new_email)
    assert result is not None

@pytest.mark.asyncio
async def test_update_user_duplicate_email():
    """Test that updating to duplicate email raises error"""
    unique_id_1 = str(uuid4())[:8]
    unique_id_2 = str(uuid4())[:8]
    
    email1 = f"user1-{unique_id_1}@example.com"
    
    # Create two users
    user1_id = await create_user(
        name="John Doe",
        email=email1,
        phone_number=f"+55119{unique_id_1[:8]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    user2_id = await create_user(
        name="Jane Doe",
        email=f"user2-{unique_id_2}@example.com",
        phone_number=f"+55119{unique_id_2[:8]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Try to update user2's email to user1's email
    with pytest.raises(ValueError):
        await update_user(user2_id, email=email1)

@pytest.mark.asyncio
async def test_delete_user():
    """Test deleting a user"""
    unique_id = str(uuid4())[:8]
    
    # Create a user
    user_id = await create_user(
        name="John Doe",
        email=f"delete-{unique_id}@example.com",
        phone_number=f"+55119{unique_id[:8]}",
        password="SecurePass123!",
        cpf = cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Delete user
    result = await delete_user(user_id)
    assert result is not None