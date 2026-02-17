import csv
import io
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.models.audit import AuditLog
from app.schemas.audit_log import AuditLogSchema, PaginatedAuditLogList

router = APIRouter(prefix="/audit-logs", tags=["audit"])


def _build_query(
    user_id: uuid.UUID | None,
    action_type: str | None,
    resource_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
):
    q = select(AuditLog)
    if user_id is not None:
        q = q.where(AuditLog.user_id == user_id)
    if action_type:
        q = q.where(AuditLog.action_type == action_type)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    if date_from:
        q = q.where(AuditLog.timestamp >= date_from)
    if date_to:
        q = q.where(AuditLog.timestamp <= date_to)
    return q


@router.get("", response_model=PaginatedAuditLogList)
async def list_audit_logs(
    current_user: Annotated[CurrentUser, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: uuid.UUID | None = Query(default=None),
    action_type: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    base_q = _build_query(user_id, action_type, resource_type, date_from, date_to)

    total = (await db.execute(select(func.count()).select_from(base_q.subquery()))).scalar_one()

    rows = (
        await db.execute(
            base_q.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()

    return PaginatedAuditLogList(
        total=total,
        items=[AuditLogSchema.model_validate(r) for r in rows],
        limit=limit,
        offset=offset,
    )


@router.get("/export")
async def export_audit_logs(
    current_user: Annotated[CurrentUser, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: uuid.UUID | None = Query(default=None),
    action_type: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
):
    base_q = _build_query(user_id, action_type, resource_type, date_from, date_to)
    rows = (
        await db.execute(base_q.order_by(AuditLog.timestamp.desc()))
    ).scalars().all()

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "timestamp", "user_id", "user_role", "action_type",
                         "resource_type", "resource_id", "ip_address", "details"])
        yield buf.getvalue()
        for row in rows:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([
                row.id, row.timestamp, row.user_id, row.user_role,
                row.action_type, row.resource_type, row.resource_id,
                row.ip_address, row.details,
            ])
            yield buf.getvalue()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )
