import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"))
    study_instance_uid: Mapped[str] = mapped_column(String, unique=True, index=True)
    study_date: Mapped[date] = mapped_column(Date)
    modality: Mapped[str] = mapped_column(String)
    referring_physician: Mapped[str | None] = mapped_column(String, nullable=True)
    study_description: Mapped[str | None] = mapped_column(String, nullable=True)
    series_description: Mapped[str | None] = mapped_column(String, nullable=True)
    file_path: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    patient = relationship("Patient", back_populates="studies")
