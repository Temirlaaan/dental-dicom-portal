import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pydicom
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.main import app
from app.models.base import Base
from app.models.patient import Patient
from app.models.study import Study


@pytest.fixture
def sync_engine():
    """Create an in-memory SQLite engine with only the tables needed for ingestion tests."""
    engine = create_engine("sqlite:///:memory:")
    # Only create tables compatible with SQLite (avoid JSONB in audit_logs)
    Patient.metadata.create_all(engine, tables=[Patient.__table__, Study.__table__])
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sync_engine):
    """Provide a transactional database session for tests (sync version)."""
    with Session(sync_engine) as session:
        yield session


# Async database fixtures for API tests
@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create an in-memory async SQLite engine for API tests."""
    from app.models import Doctor, Patient, PatientAssignment, Session, Study

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        # Only create tables compatible with SQLite (skip audit_logs with JSONB)
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                Patient.__table__,
                Study.__table__,
                Doctor.__table__,
                PatientAssignment.__table__,
                Session.__table__,
            ],
        )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session_async(async_engine):
    """Provide an async database session for API tests."""
    # Use a single connection for all operations in the test
    async with async_engine.connect() as connection:
        # Begin a transaction
        trans = await connection.begin()

        # Create session bound to this connection
        async_session_factory = sessionmaker(
            bind=connection, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session_factory() as session:
            yield session

        # Rollback at end of test
        await trans.rollback()


@pytest_asyncio.fixture
async def client(async_engine):
    """Provide an async HTTP client for API testing."""
    from app.core.database import get_db
    from app.core.security import CurrentUser, get_current_user, oauth2_scheme

    # Create a session factory for the test database
    async_session_factory = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Override get_db dependency to use test database
    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    # Mock oauth2_scheme to bypass actual token extraction
    async def mock_oauth2_scheme():
        return "mock-token"

    # Mock get_current_user to bypass Keycloak JWT validation in tests
    async def mock_get_current_user(token: str = "mock-token"):
        # Parse the token payload to determine user type
        try:
            # Decode without verification (for testing only)
            payload = jwt.decode(token, options={"verify_signature": False})
            return CurrentUser(
                id=payload.get("sub", "test-user-id"),
                username=payload.get("preferred_username", "test@test.com"),
                email=payload.get("email", "test@test.com"),
                name=payload.get("name", "Test User"),
                roles=payload.get("realm_access", {}).get("roles", []),
            )
        except Exception:
            # Fallback for invalid tokens
            return CurrentUser(
                id="test-user-id",
                username="test@test.com",
                email="test@test.com",
                name="Test User",
                roles=["doctor"],
            )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[oauth2_scheme] = mock_oauth2_scheme
    app.dependency_overrides[get_current_user] = mock_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def doctor_token():
    """Generate a mock JWT token for doctor role."""
    payload = {
        "sub": "doctor-keycloak-001",
        "preferred_username": "doctor@test.com",
        "realm_access": {"roles": ["doctor"]},
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    # Use a dummy secret for testing (not validating signature in tests)
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture
def admin_token():
    """Generate a mock JWT token for admin role."""
    payload = {
        "sub": "admin-keycloak-001",
        "preferred_username": "admin@test.com",
        "realm_access": {"roles": ["admin"]},
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture
def override_winrm_client():
    """Fixture to override WinRM client dependency."""
    from app.services.winrm_client import get_winrm_client

    def _override(mock_client):
        app.dependency_overrides[get_winrm_client] = lambda: mock_client

    yield _override
    app.dependency_overrides.clear()


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for file operations."""
    return tmp_path


def create_test_dicom(
    tmp_dir: Path,
    filename: str = "test.dcm",
    patient_id: str = "PAT001",
    patient_name: str = "DOE^JOHN",
    study_instance_uid: str | None = None,
    study_date: str = "20240115",
    modality: str = "IO",
    referring_physician: str = "SMITH^DR",
    study_description: str = "Dental Panoramic",
    series_description: str = "Pan Series",
) -> Path:
    """Create a minimal valid DICOM file for testing."""
    file_path = tmp_dir / filename

    file_meta = pydicom.Dataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1.3"
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(file_path), {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.PatientID = patient_id
    ds.PatientName = patient_name
    ds.StudyInstanceUID = study_instance_uid or generate_uid()
    ds.StudyDate = study_date
    ds.Modality = modality
    ds.ReferringPhysicianName = referring_physician
    ds.StudyDescription = study_description
    ds.SeriesDescription = series_description

    ds.save_as(str(file_path))
    return file_path
