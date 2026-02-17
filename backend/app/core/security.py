from functools import wraps
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/auth",
    tokenUrl=f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token",
    auto_error=True,
)

# Cache for Keycloak public key
_jwks_cache: dict | None = None


class CurrentUser(BaseModel):
    id: str
    username: str
    email: str
    name: str
    roles: list[str]

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    @property
    def is_doctor(self) -> bool:
        return "doctor" in self.roles


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
            )
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


def _clear_jwks_cache():
    global _jwks_cache
    _jwks_cache = None


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        jwks = await _get_jwks()
        # Get the signing key from JWKS
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = None
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = key
                break

        if rsa_key is None:
            # Key not found, maybe rotated — clear cache and retry once
            _clear_jwks_cache()
            jwks = await _get_jwks()
            for key in jwks.get("keys", []):
                if key["kid"] == unverified_header.get("kid"):
                    rsa_key = key
                    break

        if rsa_key is None:
            raise credentials_exception

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience="account",
            issuer=f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}",
        )

        user_id: str = payload.get("sub", "")
        username: str = payload.get("preferred_username", "")
        email: str = payload.get("email", "")
        name: str = payload.get("name", username)

        # Extract realm roles
        realm_access = payload.get("realm_access", {})
        roles = realm_access.get("roles", [])

        if not user_id:
            raise credentials_exception

        return CurrentUser(
            id=user_id,
            username=username,
            email=email,
            name=name,
            roles=roles,
        )
    except JWTError:
        raise credentials_exception


def require_role(role: str):
    """Dependency factory for role-based access control."""
    async def _check_role(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return current_user
    return _check_role
