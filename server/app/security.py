from datetime import UTC, datetime, timedelta

import jwt

from app.config import Settings

ALGORITHM = "HS256"


def create_access_token(user_id: int, settings: Settings) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at, "type": "access"},
        settings.app_secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str, settings: Settings) -> int:
    payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("invalid token type")
    subject = payload.get("sub")
    if not subject:
        raise jwt.InvalidTokenError("missing token subject")
    return int(subject)

