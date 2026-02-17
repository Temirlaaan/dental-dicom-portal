import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.study import Study
from app.services.dicom_parser import DicomData

logger = logging.getLogger(__name__)


class DicomIngestionService:

    def __init__(self, sync_engine):
        self._engine = sync_engine

    def ingest_dicom(self, data: DicomData, file_path: str) -> bool:
        """Ingest a parsed DICOM record into the database.

        Returns True if a new study was created, False if it was a duplicate.
        """
        with Session(self._engine) as session:
            # Check for duplicate study
            existing = session.execute(
                select(Study).where(Study.study_instance_uid == data.study_instance_uid)
            ).scalar_one_or_none()

            if existing is not None:
                logger.info("Duplicate study skipped: %s", data.study_instance_uid)
                return False

            # Get or create patient
            patient = session.execute(
                select(Patient).where(Patient.patient_id == data.patient_id)
            ).scalar_one_or_none()

            if patient is None:
                patient = Patient(
                    patient_id=data.patient_id,
                    name=data.patient_name,
                )
                session.add(patient)
                try:
                    session.flush()
                except IntegrityError:
                    # Race condition: another thread created the patient
                    session.rollback()
                    patient = session.execute(
                        select(Patient).where(Patient.patient_id == data.patient_id)
                    ).scalar_one()

            study = Study(
                patient_id=patient.id,
                study_instance_uid=data.study_instance_uid,
                study_date=data.study_date,
                modality=data.modality,
                referring_physician=data.referring_physician,
                study_description=data.study_description,
                series_description=data.series_description,
                file_path=file_path,
            )
            session.add(study)

            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                logger.info("Duplicate study (race condition): %s", data.study_instance_uid)
                return False

            logger.info(
                "Ingested study %s for patient %s",
                data.study_instance_uid,
                data.patient_id,
            )
            return True
