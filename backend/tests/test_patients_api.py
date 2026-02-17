"""
Integration tests for patient and assignment API endpoints.

Uses an async SQLite in-memory database via aiosqlite to override get_db,
and overrides get_current_user to inject test users without requiring Keycloak.
"""
import uuid
from collections.abc import AsyncGenerator
from datetime import date, datetime

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.models.assignment import PatientAssignment
from app.models.base import Base
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.study import Study

# ── Test database setup ──────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Create only the tables needed for these tests (skip JSONB audit_logs)
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                Patient.__table__,
                Study.__table__,
                Doctor.__table__,
                PatientAssignment.__table__,
            ],
        )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


# ── Shared test data fixtures ─────────────────────────────────────────────────

ADMIN_ID = str(uuid.uuid4())
DOCTOR_KC_ID = str(uuid.uuid4())
OTHER_DOCTOR_KC_ID = str(uuid.uuid4())

ADMIN_USER = CurrentUser(
    id=ADMIN_ID,
    username="admin",
    email="admin@test.com",
    name="Admin User",
    roles=["admin"],
)

DOCTOR_USER = CurrentUser(
    id=DOCTOR_KC_ID,
    username="dr_smith",
    email="dr.smith@test.com",
    name="Dr Smith",
    roles=["doctor"],
)

OTHER_DOCTOR_USER = CurrentUser(
    id=OTHER_DOCTOR_KC_ID,
    username="dr_jones",
    email="dr.jones@test.com",
    name="Dr Jones",
    roles=["doctor"],
)


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession):
    """Seed the database with test patients, doctors, studies, and assignments."""
    # Patients
    patient_a = Patient(id=uuid.uuid4(), patient_id="PAT001", name="Alice Anderson")
    patient_b = Patient(id=uuid.uuid4(), patient_id="PAT002", name="Bob Brown")
    db_session.add_all([patient_a, patient_b])

    # Doctors
    doctor = Doctor(
        id=uuid.uuid4(),
        keycloak_user_id=DOCTOR_KC_ID,
        name="Dr Smith",
        email="dr.smith@test.com",
    )
    other_doctor = Doctor(
        id=uuid.uuid4(),
        keycloak_user_id=OTHER_DOCTOR_KC_ID,
        name="Dr Jones",
        email="dr.jones@test.com",
    )
    db_session.add_all([doctor, other_doctor])

    # Study for patient_a
    study = Study(
        id=uuid.uuid4(),
        patient_id=patient_a.id,
        study_instance_uid="1.2.3.4.5",
        study_date=date(2024, 1, 15),
        modality="IO",
        file_path="/tmp/test.dcm",
    )
    db_session.add(study)

    # Assign patient_a to doctor (not patient_b)
    assignment = PatientAssignment(
        id=uuid.uuid4(),
        patient_id=patient_a.id,
        doctor_id=doctor.id,
        assigned_by=uuid.UUID(ADMIN_ID),
    )
    db_session.add(assignment)

    await db_session.commit()
    await db_session.refresh(patient_a)
    await db_session.refresh(patient_b)
    await db_session.refresh(doctor)
    await db_session.refresh(other_doctor)
    await db_session.refresh(assignment)

    return {
        "patient_a": patient_a,
        "patient_b": patient_b,
        "doctor": doctor,
        "other_doctor": other_doctor,
        "study": study,
        "assignment": assignment,
    }


def make_client(db_session: AsyncSession, current_user: CurrentUser) -> AsyncClient:
    """Build an AsyncClient with get_db and get_current_user overridden."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Patient endpoint tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_patients_admin_sees_all(db_session, seed_data):
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.get("/api/patients")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_patients_doctor_scoped(db_session, seed_data):
    async with make_client(db_session, DOCTOR_USER) as client:
        resp = await client.get("/api/patients")
    assert resp.status_code == 200
    data = resp.json()
    # Doctor is only assigned to patient_a
    assert data["total"] == 1
    assert data["items"][0]["patient_id"] == "PAT001"


@pytest.mark.asyncio
async def test_list_patients_unregistered_doctor_sees_nothing(db_session, seed_data):
    """A user with doctor role but no Doctor record in DB sees no patients."""
    unregistered = CurrentUser(
        id=str(uuid.uuid4()),
        username="ghost",
        email="ghost@test.com",
        name="Ghost",
        roles=["doctor"],
    )
    async with make_client(db_session, unregistered) as client:
        resp = await client.get("/api/patients")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_patients(db_session, seed_data):
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.get("/api/patients", params={"search": "alice"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Alice Anderson"


@pytest.mark.asyncio
async def test_pagination(db_session, seed_data):
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.get("/api/patients", params={"limit": 1, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_get_patient_admin(db_session, seed_data):
    patient_id = str(seed_data["patient_a"].id)
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.get(f"/api/patients/{patient_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["patient_id"] == "PAT001"
    assert data["study_count"] == 1
    assert len(data["studies"]) == 1


@pytest.mark.asyncio
async def test_get_patient_not_assigned_returns_404(db_session, seed_data):
    """Doctor accessing a patient not assigned to them gets 404, not 403."""
    patient_id = str(seed_data["patient_b"].id)
    async with make_client(db_session, DOCTOR_USER) as client:
        resp = await client.get(f"/api/patients/{patient_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_patient_studies(db_session, seed_data):
    patient_id = str(seed_data["patient_a"].id)
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.get(f"/api/patients/{patient_id}/studies")
    assert resp.status_code == 200
    studies = resp.json()
    assert len(studies) == 1
    assert studies[0]["study_instance_uid"] == "1.2.3.4.5"


# ── Assignment endpoint tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_assignments_admin(db_session, seed_data):
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.get("/api/assignments")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_create_assignment_admin_only(db_session, seed_data):
    body = {
        "patient_id": str(seed_data["patient_b"].id),
        "doctor_id": str(seed_data["doctor"].id),
    }
    async with make_client(db_session, DOCTOR_USER) as client:
        resp = await client.post("/api/assignments", json=body)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_assignment(db_session, seed_data):
    body = {
        "patient_id": str(seed_data["patient_b"].id),
        "doctor_id": str(seed_data["doctor"].id),
    }
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.post("/api/assignments", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["patient_id"] == str(seed_data["patient_b"].id)
    assert data["doctor_id"] == str(seed_data["doctor"].id)


@pytest.mark.asyncio
async def test_create_assignment_duplicate_rejected(db_session, seed_data):
    body = {
        "patient_id": str(seed_data["patient_a"].id),
        "doctor_id": str(seed_data["doctor"].id),
    }
    # patient_a is already assigned to doctor in seed_data
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.post("/api/assignments", json=body)
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_delete_assignment(db_session, seed_data):
    assignment_id = str(seed_data["assignment"].id)
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.delete(f"/api/assignments/{assignment_id}")
    assert resp.status_code == 204

    # Verify it's gone
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.get("/api/assignments")
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_assignment_not_found(db_session, seed_data):
    fake_id = str(uuid.uuid4())
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.delete(f"/api/assignments/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_assignments_filter_by_doctor(db_session, seed_data):
    doctor_id = str(seed_data["doctor"].id)
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.get("/api/assignments", params={"doctor_id": doctor_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    other_doctor_id = str(seed_data["other_doctor"].id)
    async with make_client(db_session, ADMIN_USER) as client:
        resp = await client.get("/api/assignments", params={"doctor_id": other_doctor_id})
    assert resp.status_code == 200
    assert len(resp.json()) == 0
