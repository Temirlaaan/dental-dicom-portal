from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.study import Study
from app.services.dicom_ingestion import DicomIngestionService
from app.services.dicom_parser import DicomData


def _make_dicom_data(**overrides) -> DicomData:
    defaults = dict(
        patient_id="PAT001",
        patient_name="Doe, John",
        study_instance_uid="1.2.3.4.5.6.7.8.9",
        study_date=date(2024, 1, 15),
        modality="IO",
        referring_physician="Dr. Smith",
        study_description="Dental Panoramic",
        series_description="Pan Series",
    )
    defaults.update(overrides)
    return DicomData(**defaults)


class TestDicomIngestion:
    def test_new_patient_and_study(self, sync_engine):
        svc = DicomIngestionService(sync_engine)
        data = _make_dicom_data()

        result = svc.ingest_dicom(data, "/mnt/dicom-export/test.dcm")
        assert result is True

        with Session(sync_engine) as session:
            patient = session.execute(
                select(Patient).where(Patient.patient_id == "PAT001")
            ).scalar_one()
            assert patient.name == "Doe, John"

            study = session.execute(
                select(Study).where(Study.study_instance_uid == "1.2.3.4.5.6.7.8.9")
            ).scalar_one()
            assert study.patient_id == patient.id
            assert study.modality == "IO"

    def test_existing_patient_new_study(self, sync_engine):
        svc = DicomIngestionService(sync_engine)

        # First study
        data1 = _make_dicom_data()
        svc.ingest_dicom(data1, "/mnt/dicom-export/test1.dcm")

        # Second study for same patient
        data2 = _make_dicom_data(study_instance_uid="1.2.3.4.5.6.7.8.10")
        result = svc.ingest_dicom(data2, "/mnt/dicom-export/test2.dcm")
        assert result is True

        with Session(sync_engine) as session:
            patients = session.execute(select(Patient)).scalars().all()
            assert len(patients) == 1

            studies = session.execute(select(Study)).scalars().all()
            assert len(studies) == 2

    def test_duplicate_study_skipped(self, sync_engine):
        svc = DicomIngestionService(sync_engine)
        data = _make_dicom_data()

        result1 = svc.ingest_dicom(data, "/mnt/dicom-export/test.dcm")
        assert result1 is True

        result2 = svc.ingest_dicom(data, "/mnt/dicom-export/test.dcm")
        assert result2 is False

        with Session(sync_engine) as session:
            studies = session.execute(select(Study)).scalars().all()
            assert len(studies) == 1

    def test_different_patients(self, sync_engine):
        svc = DicomIngestionService(sync_engine)

        data1 = _make_dicom_data()
        data2 = _make_dicom_data(
            patient_id="PAT002",
            patient_name="Smith, Jane",
            study_instance_uid="9.8.7.6.5",
        )

        svc.ingest_dicom(data1, "/mnt/dicom-export/test1.dcm")
        svc.ingest_dicom(data2, "/mnt/dicom-export/test2.dcm")

        with Session(sync_engine) as session:
            patients = session.execute(select(Patient)).scalars().all()
            assert len(patients) == 2
