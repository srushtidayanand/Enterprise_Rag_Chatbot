"""
Authentication Module - JWT Token Management
Handles user login, token generation, and verification
"""

import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from pydantic import BaseModel

SECRET_KEY = "your-enterprise-rag-secret-key-change-in-production-12345"
ALGORITHM = "HS256"
TOKEN_EXPIRATION_HOURS = 24

# ==================== MODELS ====================

class LoginRequest(BaseModel):
    username: str
    password: str
    role: str  # "employee", "hr", "manager"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    role: str
    username: str


class TokenPayload(BaseModel):
    username: str
    role: str
    exp: datetime


# ==================== USER DATABASE ====================
# NOTE: In production, use a real database (PostgreSQL, MongoDB, etc.)

USERS_DB = {
    "john": {
        "password_hash": hashlib.sha256(b"password123").hexdigest(),
        "role": "employee"
    },
    "alice": {
        "password_hash": hashlib.sha256(b"password123").hexdigest(),
        "role": "hr"
    },
    "bob": {
        "password_hash": hashlib.sha256(b"password123").hexdigest(),
        "role": "manager"
    },
    "admin": {
        "password_hash": hashlib.sha256(b"admin123").hexdigest(),
        "role": "admin"
    }
}

VALID_ROLES = ["employee", "hr", "manager", "admin"]


# ==================== AUTHENTICATION FUNCTIONS ====================

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return hash_password(plain_password) == hashed_password


def authenticate_user(username: str, password: str, role: str) -> Optional[Dict]:
    """
    Authenticate user with username, password, and role.
    
    Args:
        username: Username
        password: Plain text password
        role: Requested role
    
    Returns:
        User dict if authenticated, None otherwise
    """
    if username not in USERS_DB:
        return None
    
    user = USERS_DB[username]
    
    # Verify password
    if not verify_password(password, user["password_hash"]):
        return None
    
    # Verify role matches
    if role not in VALID_ROLES or user["role"] != role:
        return None
    
    return {
        "username": username,
        "role": user["role"]
    }


def create_access_token(data: Dict) -> tuple[str, int]:
    """
    Create JWT access token.
    
    Args:
        data: Payload data (username, role)
    
    Returns:
        Tuple of (token, expires_in_seconds)
    """
    expires = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION_HOURS)
    to_encode = data.copy()
    to_encode.update({"exp": expires})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    expires_in = int(TOKEN_EXPIRATION_HOURS * 3600)
    
    return encoded_jwt, expires_in


def verify_token(token: str) -> Optional[Dict]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
        role = payload.get("role")
        
        if username is None or role is None:
            return None
        
        return {"username": username, "role": role}
    
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    
    except jwt.InvalidTokenError:
        return None  # Invalid token


def create_user(username: str, password: str, role: str) -> bool:
    """
    Create new user (admin only).
    
    Args:
        username: New username
        password: New password
        role: User role
    
    Returns:
        True if created, False if already exists
    """
    if username in USERS_DB:
        return False
    
    if role not in VALID_ROLES:
        return False
    
    USERS_DB[username] = {
        "password_hash": hash_password(password),
        "role": role
    }
    return True


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """
    Change user password.
    
    Args:
        username: Username
        old_password: Current password
        new_password: New password
    
    Returns:
        True if changed, False if failed
    """
    if username not in USERS_DB:
        return False
    
    user = USERS_DB[username]
    
    if not verify_password(old_password, user["password_hash"]):
        return False
    
    user["password_hash"] = hash_password(new_password)
    return True


# ==================== SESSION MANAGEMENT ====================

# In-memory token blacklist (use Redis in production)
TOKEN_BLACKLIST = set()


def logout_token(token: str) -> None:
    """Add token to blacklist (logout)"""
    TOKEN_BLACKLIST.add(token)


def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted"""
    return token in TOKEN_BLACKLIST
