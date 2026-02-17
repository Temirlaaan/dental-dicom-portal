import logging
import uuid

from jose import jwt as jose_jwt
from jose.exceptions import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.database import async_session_factory
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

_LOGGED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _parse_path(path: str) -> tuple[str, str | None]:
    """
    Extract (resource_type, resource_id) from a URL path.

    /api/patients/abc-123        -> ("patients", "abc-123")
    /api/assignments             -> ("assignments", None)
    /api/assignments/xyz/foo     -> ("assignments", "xyz")
    """
    parts = [p for p in path.strip("/").split("/") if p]
    # Strip leading "api" segment if present
    if parts and parts[0] == "api":
        parts = parts[1:]
    resource_type = parts[0] if parts else "unknown"
    resource_id = parts[1] if len(parts) > 1 else None
    return resource_type, resource_id


def _method_to_action(method: str) -> str:
    return {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }.get(method.upper(), method.lower())


def _extract_user(request: Request) -> tuple[uuid.UUID | None, str | None]:
    """Decode JWT claims without verification for audit logging only."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, None
    token = auth[len("Bearer "):]
    try:
        claims = jose_jwt.get_unverified_claims(token)
        raw_id = claims.get("sub")
        user_id = uuid.UUID(raw_id) if raw_id else None
        roles = claims.get("realm_access", {}).get("roles", [])
        user_role = roles[0] if roles else None
        return user_id, user_role
    except (JWTError, ValueError, AttributeError):
        return None, None


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.method not in _LOGGED_METHODS:
            return response
        if response.status_code >= 400:
            return response

        try:
            user_id, user_role = _extract_user(request)
            resource_type, resource_id = _parse_path(request.url.path)
            action_type = _method_to_action(request.method)
            ip_address = _client_ip(request)

            async with async_session_factory() as session:
                entry = AuditLog(
                    user_id=user_id,
                    user_role=user_role,
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details={"status_code": response.status_code, "path": request.url.path},
                    ip_address=ip_address,
                )
                session.add(entry)
                await session.commit()
        except Exception:
            logger.exception("Audit logging failed — request continues normally")

        return response
