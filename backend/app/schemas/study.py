import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StudySchema(BaseModel):
    id: uuid.UUID
    study_instance_uid: str
    study_date: date
    modality: str
    referring_physician: str | None
    study_description: str | None
    series_description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
