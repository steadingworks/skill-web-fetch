"""JWT validation dependency for skill-web-fetch API endpoints."""

from __future__ import annotations

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings

_bearer = HTTPBearer()


def require_jwt(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> dict:
    """Validate RS256 JWT. Returns decoded payload on success.

    Raises:
        401 — token missing, malformed, or expired
        403 — token scope insufficient
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.public_key_pem,
            algorithms=["RS256"],
            options={"require": ["exp", "iss", "scope"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired — re-acquire via /token",
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )

    if payload.get("iss") != settings.jwt_issuer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token issuer mismatch",
        )
    if "skill-api" not in payload.get("scope", "").split():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token scope insufficient",
        )

    return payload
