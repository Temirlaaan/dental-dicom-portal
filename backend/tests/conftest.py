import tempfile
from datetime import date
from pathlib import Path

import pydicom
import pytest
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
    """Provide a transactional database session for tests."""
    with Session(sync_engine) as session:
        yield session


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
