import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.models.assignment import PatientAssignment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.assignment import AssignmentCreate, AssignmentSchema

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.post("", response_model=AssignmentSchema, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    body: AssignmentCreate,
    current_user: Annotated[CurrentUser, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Validate patient exists
    patient = (await db.execute(select(Patient).where(Patient.id == body.patient_id))).scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Validate doctor exists
    doctor = (await db.execute(select(Doctor).where(Doctor.id == body.doctor_id))).scalar_one_or_none()
    if doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    # Check for duplicate
    existing = (
        await db.execute(
            select(PatientAssignment).where(
                PatientAssignment.patient_id == body.patient_id,
                PatientAssignment.doctor_id == body.doctor_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment already exists")

    assignment = PatientAssignment(
        patient_id=body.patient_id,
        doctor_id=body.doctor_id,
        assigned_by=uuid.UUID(current_user.id),
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return AssignmentSchema.model_validate(assignment)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    assignment = (
        await db.execute(select(PatientAssignment).where(PatientAssignment.id == assignment_id))
    ).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await db.delete(assignment)
    await db.commit()


@router.get("", response_model=list[AssignmentSchema])
async def list_assignments(
    current_user: Annotated[CurrentUser, Depends(require_role("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    patient_id: uuid.UUID | None = Query(default=None),
    doctor_id: uuid.UUID | None = Query(default=None),
):
    query = select(PatientAssignment)
    if patient_id is not None:
        query = query.where(PatientAssignment.patient_id == patient_id)
    if doctor_id is not None:
        query = query.where(PatientAssignment.doctor_id == doctor_id)
    result = await db.execute(query)
    return [AssignmentSchema.model_validate(a) for a in result.scalars().all()]
