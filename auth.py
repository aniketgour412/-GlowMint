import os
import hmac
import hashlib
import secrets
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import jwt
from config import APP_SECRET_KEY, ADMIN_SESSION_EXPIRE_HOURS

PBKDF2_ITERATIONS = 310_000

def hash_password(password: str) -> Tuple[str, str]:
    """Generate a random salt and compute pbkdf2_hmac sha256 hash."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        PBKDF2_ITERATIONS
    ).hex()
    return pwd_hash, salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify password against stored hash and salt."""
    computed_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        PBKDF2_ITERATIONS
    ).hex()
    return secrets.compare_digest(computed_hash, stored_hash)

def create_admin_token(user_id: int, username: str, email: str) -> str:
    """Create a signed JWT token for admin session."""
    expire = datetime.now(timezone.utc) + timedelta(hours=ADMIN_SESSION_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "email": email,
        "role": "admin",
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, APP_SECRET_KEY, algorithm="HS256")

def decode_admin_token(token: str) -> Optional[dict]:
    """Decode and validate an admin JWT token."""
    try:
        payload = jwt.decode(token, APP_SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        return None
