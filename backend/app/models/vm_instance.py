import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VMInstance(Base):
    __tablename__ = "vm_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname: Mapped[str] = mapped_column(String, unique=True)
    ip_address: Mapped[str] = mapped_column(String, unique=True)
    rdp_port: Mapped[int] = mapped_column(default=3389)
    winrm_port: Mapped[int] = mapped_column(default=5985)
    status: Mapped[str] = mapped_column(String, default="ready", index=True)
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    mounted_share: Mapped[str | None] = mapped_column(String, nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_health_check: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
