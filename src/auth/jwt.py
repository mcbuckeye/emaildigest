"""JWT token utilities."""

from datetime import datetime, timedelta

from jose import JWTError, jwt

from src.config import config


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=config().access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config().secret_key, algorithm=config().algorithm)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify JWT access token and return payload."""
    try:
        payload = jwt.decode(token, config().secret_key, algorithms=[config().algorithm])
        return payload
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
