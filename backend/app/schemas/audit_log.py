import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogSchema(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    user_id: uuid.UUID | None
    user_role: str | None
    action_type: str
    resource_type: str
    resource_id: str | None
    details: dict | None
    ip_address: str | None

    model_config = ConfigDict(from_attributes=True)


class PaginatedAuditLogList(BaseModel):
    total: int
    items: list[AuditLogSchema]
    limit: int
    offset: int
