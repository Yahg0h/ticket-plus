from uuid import uuid4

import pytest
from validate_docbr import CPF

from app.services.auth_service import (
    authenticate_user,
    create_jwt_token,
    create_user,
    decode_token,
    hash_password,
    verify_password,
)

cpf_gen = CPF()

@pytest.mark.asyncio
async def test_create_user_success():
    """Test successful user creation"""
    unique_id = str(uuid4())[:8]
    
    user_id = await create_user(
        name="John Doe",
        email=f"john-{unique_id}@example.com",
        phone_number=f"+55119{unique_id[:8]}",
        password="SecurePass123!",
        cpf=cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    assert user_id is not None
    assert isinstance(user_id, int)
    assert user_id > 0

@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    """Test that duplicate email raises ValueError"""
    unique_id = str(uuid4())[:8]
    email = f"john-{unique_id}@example.com"
    
    # Create first user
    await create_user(
        name="John Doe",
        email=email,
        phone_number=f"+55119{unique_id[:8]}",
        password="SecurePass123!",
        cpf=cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Try to create another with same email
    unique_id_2 = str(uuid4())[:8]
    with pytest.raises(ValueError):
        await create_user(
            name="Jane Doe",
            email=email,
            phone_number=f"+55119{unique_id_2[:8]}",
            password="SecurePass123!",
            cpf=cpf_gen.generate(mask=True),
            state="SP",
            city="São Paulo"
        )

@pytest.mark.asyncio
async def test_authenticate_user_with_email():
    """Test user authentication with email"""
    unique_id = str(uuid4())[:8]
    email = f"auth-{unique_id}@example.com"
    password = "SecurePass123!"
    
    # Create user
    await create_user(
        name="John Doe",
        email=email,
        phone_number=f"+55119{unique_id[:8]}",
        password=password,
        cpf=cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Authenticate with email
    user = await authenticate_user(
        email=email,
        phone_number=None,
        password=password
    )
    
    assert user is not None
    assert user["email"] == email

@pytest.mark.asyncio
async def test_authenticate_user_with_phone():
    """Test user authentication with phone"""
    unique_id = str(uuid4())[:8]
    phone = f"+55 11 9{unique_id}0000"
    password = "SecurePass123!"
    
    # Create user
    await create_user(
        name="John Doe",
        email=f"phone-{unique_id}@example.com",
        phone_number=phone,
        password=password,
        cpf=cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Authenticate with phone
    user = await authenticate_user(
        email=None,
        phone_number=phone,
        password=password
    )
    
    assert user is not None
    assert user["phone_number"] == phone

@pytest.mark.asyncio
async def test_authenticate_user_invalid_password():
    """Test authentication fails with wrong password"""
    unique_id = str(uuid4())[:8]
    email = f"invalid-{unique_id}@example.com"
    
    # Create user
    await create_user(
        name="John Doe",
        email=email,
        phone_number=f"+55119{unique_id[:8]}",
        password="CorrectPassword123!",
        cpf=cpf_gen.generate(mask=True),
        state="SP",
        city="São Paulo"
    )
    
    # Try with wrong password
    user = await authenticate_user(
        email=email,
        phone_number=None,
        password="WrongPassword123!"
    )
    
    assert user is None

@pytest.mark.asyncio
async def test_authenticate_user_not_found():
    """Test authentication returns None for non-existent user"""
    user = await authenticate_user(
        email="nonexistent@example.com",
        phone_number=None,
        password="Password123!"
    )
    
    assert user is None

def test_create_jwt_token():
    """Test JWT token creation"""
    user_id = 12345
    token = create_jwt_token(user_id)
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

def test_decode_token():
    """Test JWT token decoding"""
    user_id = 12345
    token = create_jwt_token(user_id)
    
    decoded_user_id = decode_token(token)
    
    assert decoded_user_id == user_id

def test_decode_token_invalid():
    """Test decoding invalid token"""
    with pytest.raises(ValueError):
        decode_token("invalid.token.here")

def test_verify_password():
    """Test password verification"""
    
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    
    # Correct password should verify
    assert verify_password(password, hashed) is True
    
    # Wrong password should not verify
    assert verify_password("WrongPassword", hashed) is False