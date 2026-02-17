import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.patient import Patient
from app.models.study import Study
from app.schemas.patient import PaginatedPatientList, PatientDetail, PatientSchema
from app.schemas.study import StudySchema
from app.services.patients import get_accessible_patients_query

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=PaginatedPatientList)
async def list_patients(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None),
    study_date_from: date | None = Query(default=None),
    study_date_to: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    base_query = await get_accessible_patients_query(db, current_user)

    if search:
        base_query = base_query.where(Patient.name.ilike(f"%{search}%"))

    if study_date_from or study_date_to:
        base_query = base_query.join(Study, Study.patient_id == Patient.id)
        if study_date_from:
            base_query = base_query.where(Study.study_date >= study_date_from)
        if study_date_to:
            base_query = base_query.where(Study.study_date <= study_date_to)
        base_query = base_query.distinct()

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    # Fetch page with study_count via correlated subquery
    study_count_subq = (
        select(func.count(Study.id))
        .where(Study.patient_id == Patient.id)
        .correlate(Patient)
        .scalar_subquery()
    )
    paged_query = (
        base_query.add_columns(study_count_subq.label("study_count"))
        .order_by(Patient.name)
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(paged_query)).all()

    items = [
        PatientSchema(
            id=row.Patient.id,
            patient_id=row.Patient.patient_id,
            name=row.Patient.name,
            created_at=row.Patient.created_at,
            study_count=row.study_count,
        )
        for row in rows
    ]

    return PaginatedPatientList(total=total, items=items, limit=limit, offset=offset)


@router.get("/{patient_id}", response_model=PatientDetail)
async def get_patient(
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    base_query = await get_accessible_patients_query(db, current_user)
    result = await db.execute(
        base_query.where(Patient.id == patient_id).options(selectinload(Patient.studies))
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    return PatientDetail(
        id=patient.id,
        patient_id=patient.patient_id,
        name=patient.name,
        created_at=patient.created_at,
        study_count=len(patient.studies),
        studies=[StudySchema.model_validate(s) for s in patient.studies],
    )


@router.get("/{patient_id}/studies", response_model=list[StudySchema])
async def list_patient_studies(
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    base_query = await get_accessible_patients_query(db, current_user)
    result = await db.execute(
        base_query.where(Patient.id == patient_id).options(selectinload(Patient.studies))
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    return [StudySchema.model_validate(s) for s in patient.studies]
