import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.study import StudySchema


class PatientSchema(BaseModel):
    id: uuid.UUID
    patient_id: str
    name: str
    created_at: datetime
    study_count: int

    model_config = ConfigDict(from_attributes=True)


class PatientDetail(PatientSchema):
    studies: list[StudySchema]


class PaginatedPatientList(BaseModel):
    total: int
    items: list[PatientSchema]
    limit: int
    offset: int
