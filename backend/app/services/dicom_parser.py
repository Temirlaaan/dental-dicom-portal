import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pydicom

logger = logging.getLogger(__name__)


@dataclass
class DicomData:
    patient_id: str
    patient_name: str
    study_instance_uid: str
    study_date: date
    modality: str
    referring_physician: str | None
    study_description: str | None
    series_description: str | None


def _format_patient_name(raw_name: str) -> str:
    """Convert DICOM 'LAST^FIRST' format to 'Last, First'."""
    if not raw_name:
        return ""
    parts = raw_name.split("^")
    if len(parts) >= 2:
        return f"{parts[0].strip().title()}, {parts[1].strip().title()}"
    return parts[0].strip().title()


def _parse_study_date(raw_date: str) -> date | None:
    """Parse DICOM date string (YYYYMMDD) to date object."""
    if not raw_date or len(raw_date) < 8:
        return None
    try:
        return date(int(raw_date[:4]), int(raw_date[4:6]), int(raw_date[6:8]))
    except (ValueError, IndexError):
        return None


class DicomTagExtractor:

    @staticmethod
    def extract_tags(file_path: Path) -> DicomData | None:
        """Extract DICOM tags from a file. Returns None if file is invalid or missing required tags."""
        try:
            ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
        except Exception:
            logger.warning("Failed to read DICOM file: %s", file_path)
            return None

        # Required tags
        patient_id = str(getattr(ds, "PatientID", "")).strip()
        patient_name = str(getattr(ds, "PatientName", "")).strip()
        study_instance_uid = str(getattr(ds, "StudyInstanceUID", "")).strip()
        study_date_raw = str(getattr(ds, "StudyDate", "")).strip()
        modality = str(getattr(ds, "Modality", "")).strip()

        if not patient_id or not study_instance_uid:
            logger.warning("Missing required DICOM tags (PatientID or StudyInstanceUID) in: %s", file_path)
            return None

        study_date = _parse_study_date(study_date_raw)
        if study_date is None:
            logger.warning("Invalid or missing StudyDate in: %s", file_path)
            return None

        # Optional tags
        referring_physician = str(getattr(ds, "ReferringPhysicianName", "")).strip() or None
        study_description = str(getattr(ds, "StudyDescription", "")).strip() or None
        series_description = str(getattr(ds, "SeriesDescription", "")).strip() or None

        return DicomData(
            patient_id=patient_id,
            patient_name=_format_patient_name(patient_name),
            study_instance_uid=study_instance_uid,
            study_date=study_date,
            modality=modality or "OT",
            referring_physician=referring_physician,
            study_description=study_description,
            series_description=series_description,
        )
