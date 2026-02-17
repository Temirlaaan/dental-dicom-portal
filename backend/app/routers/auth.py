from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

KC_BASE = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect"
FRONTEND_URL = "http://10.121.245.146:5173"


@router.get("/login")
async def login(redirect_uri: str = Query(default=f"{FRONTEND_URL}/auth/callback")):
    """Redirect to Keycloak login page."""
    params = urlencode({
        "client_id": settings.KEYCLOAK_FRONTEND_CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": redirect_uri,
    })
    return RedirectResponse(url=f"{KC_BASE}/auth?{params}")


@router.get("/callback")
async def callback(code: str, redirect_uri: str = Query(default=f"{FRONTEND_URL}/auth/callback")):
    """Exchange authorization code for tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{KC_BASE}/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KEYCLOAK_FRONTEND_CLIENT_ID,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        resp.raise_for_status()
        return resp.json()


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh an access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{KC_BASE}/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.KEYCLOAK_FRONTEND_CLIENT_ID,
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        return resp.json()


@router.get("/me")
async def get_me(current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    """Get current authenticated user info."""
    return current_user


@router.get("/logout")
async def logout(redirect_uri: str = Query(default=FRONTEND_URL)):
    """Redirect to Keycloak logout."""
    params = urlencode({
        "client_id": settings.KEYCLOAK_FRONTEND_CLIENT_ID,
        "post_logout_redirect_uri": redirect_uri,
    })
    return RedirectResponse(url=f"{KC_BASE}/logout?{params}")
