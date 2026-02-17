import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctors.id"))
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"))
    study_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("studies.id"), nullable=True)
    guacamole_connection_id: Mapped[str | None] = mapped_column(String, nullable=True)
    rds_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    windows_user: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="creating", index=True)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_activity_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
