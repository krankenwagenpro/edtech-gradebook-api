"""Password hashing and JWT helpers."""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

# In production set SECRET_KEY and TEACHER_INVITE_CODE as environment variables.
# The defaults below are for local development only.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key-change-me-in-production-0000")
TEACHER_INVITE_CODE = os.getenv("TEACHER_INVITE_CODE", "dev-teacher-code")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Return the username from a valid token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
