import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssignmentCreate(BaseModel):
    patient_id: uuid.UUID
    doctor_id: uuid.UUID


class AssignmentSchema(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    assigned_by: uuid.UUID | None
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)
