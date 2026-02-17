"""Pydantic schemas for session resources."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    """Request schema for creating a new session."""

    patient_id: uuid.UUID


class SessionSchema(BaseModel):
    """Response schema for session resources."""

    id: uuid.UUID
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
    study_id: uuid.UUID | None
    guacamole_connection_id: str | None
    rds_session_id: str | None
    windows_user: str | None
    status: str
    started_at: datetime
    last_activity_at: datetime | None
    ended_at: datetime | None

    model_config = {"from_attributes": True}
