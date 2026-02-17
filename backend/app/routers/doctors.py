import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.models.doctor import Doctor

router = APIRouter(prefix="/doctors", tags=["doctors"])


class DoctorSchema(BaseModel):
    id: uuid.UUID
    keycloak_user_id: str
    name: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[DoctorSchema])
async def list_doctors(
    current_user: Annotated[CurrentUser, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Doctor).order_by(Doctor.name))
    return [DoctorSchema.model_validate(d) for d in result.scalars().all()]
