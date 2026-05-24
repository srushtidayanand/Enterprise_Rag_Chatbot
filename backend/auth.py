import os
import re
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
from pydantic import BaseModel
from database import get_session, User, TokenBlacklist, _hash, _verify_hash

# Load .env
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

SECRET_KEY = os.environ.get("JWT_SECRET", "fallback-secret-change-this")
ALGORITHM = "HS256"
TOKEN_EXPIRATION_HOURS = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
VALID_ROLES = ["employee", "hr", "manager", "admin"]


class LoginRequest(BaseModel):
    username: str
    password: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    role: str
    username: str


def _validate_password_complexity(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "OK"


def verify_password(plain: str, hashed: str) -> bool:
    return _verify_hash(plain, hashed)


def authenticate_user(username: str, password: str, role: str) -> Optional[Dict]:
    with get_session() as session:
        user = session.query(User).filter(User.username == username, User.is_active == 1).first()
        if not user:
            return None

        # Check account lockout
        if user.locked_until and datetime.utcnow() < user.locked_until:
            remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
            raise ValueError(f"Account locked. Try again in {remaining} minute(s).")

        if not verify_password(password, user.password_hash):
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_attempts = 0
                raise ValueError(f"Too many failed attempts. Account locked for {LOCKOUT_MINUTES} minutes.")
            return None

        if role not in VALID_ROLES or user.role != role:
            return None

        # Reset failed attempts on successful login
        user.failed_attempts = 0
        user.locked_until = None
        return {"username": username, "role": user.role}


def create_access_token(data: Dict):
    expires = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION_HOURS)
    to_encode = {**data, "exp": expires}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM), int(TOKEN_EXPIRATION_HOURS * 3600)


def verify_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("username") and payload.get("role"):
            return {"username": payload["username"], "role": payload["role"]}
    except Exception:
        pass
    return None


def create_user(username: str, password: str, role: str) -> bool:
    if role not in VALID_ROLES:
        return False
    valid, msg = _validate_password_complexity(password)
    if not valid:
        raise ValueError(msg)
    with get_session() as session:
        if session.query(User).filter_by(username=username).first():
            return False
        session.add(User(username=username, password_hash=_hash(password), role=role))
        return True


def change_password(username: str, old_password: str, new_password: str) -> bool:
    valid, msg = _validate_password_complexity(new_password)
    if not valid:
        raise ValueError(msg)
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user or not verify_password(old_password, user.password_hash):
            return False
        user.password_hash = _hash(new_password)
        return True


def logout_token(token: str):
    with get_session() as session:
        if not session.query(TokenBlacklist).filter_by(token=token).first():
            session.add(TokenBlacklist(token=token))


def cleanup_expired_tokens():
    """Remove tokens older than 24 hours from blacklist."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    with get_session() as session:
        session.query(TokenBlacklist).filter(TokenBlacklist.created_at < cutoff).delete()


def is_token_blacklisted(token: str) -> bool:
    with get_session() as session:
        return session.query(TokenBlacklist).filter_by(token=token).first() is not None


def get_all_users():
    with get_session() as session:
        users = session.query(User).all()
        return [
            {
                "username": u.username,
                "role": u.role,
                "created_at": str(u.created_at),
                "is_active": u.is_active,
                "failed_attempts": u.failed_attempts or 0,
                "locked_until": str(u.locked_until) if u.locked_until else None,
            }
            for u in users
        ]
