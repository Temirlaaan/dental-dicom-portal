from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.assignment import PatientAssignment


async def get_doctor_by_keycloak_id(db: AsyncSession, keycloak_id: str) -> Doctor | None:
    result = await db.execute(
        select(Doctor).where(Doctor.keycloak_user_id == keycloak_id)
    )
    return result.scalar_one_or_none()


async def get_accessible_patients_query(db: AsyncSession, user: CurrentUser):
    """
    Return a SELECT query filtered by user role:
    - Admin: all patients
    - Doctor: only patients assigned via patient_assignments table
    """
    if user.is_admin:
        return select(Patient)

    doctor = await get_doctor_by_keycloak_id(db, user.id)
    if doctor is None:
        # Doctor has no record in DB; return query that yields nothing
        return select(Patient).where(False)

    return (
        select(Patient)
        .join(PatientAssignment, PatientAssignment.patient_id == Patient.id)
        .where(PatientAssignment.doctor_id == doctor.id)
    )
