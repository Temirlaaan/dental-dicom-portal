from pathlib import Path

from app.services.dicom_parser import DicomTagExtractor, _format_patient_name, _parse_study_date
from tests.conftest import create_test_dicom


class TestFormatPatientName:
    def test_last_first(self):
        assert _format_patient_name("DOE^JOHN") == "Doe, John"

    def test_single_name(self):
        assert _format_patient_name("DOE") == "Doe"

    def test_empty(self):
        assert _format_patient_name("") == ""

    def test_extra_components(self):
        assert _format_patient_name("DOE^JOHN^MR") == "Doe, John"


class TestParseStudyDate:
    def test_valid_date(self):
        from datetime import date
        assert _parse_study_date("20240115") == date(2024, 1, 15)

    def test_empty(self):
        assert _parse_study_date("") is None

    def test_short(self):
        assert _parse_study_date("2024") is None

    def test_invalid(self):
        assert _parse_study_date("20241301") is None


class TestDicomTagExtractor:
    def test_valid_file(self, tmp_path):
        dcm_path = create_test_dicom(tmp_path)
        data = DicomTagExtractor.extract_tags(dcm_path)

        assert data is not None
        assert data.patient_id == "PAT001"
        assert data.patient_name == "Doe, John"
        assert data.modality == "IO"
        assert data.study_description == "Dental Panoramic"
        assert data.series_description == "Pan Series"

    def test_missing_patient_id(self, tmp_path):
        dcm_path = create_test_dicom(tmp_path, patient_id="")
        data = DicomTagExtractor.extract_tags(dcm_path)
        assert data is None

    def test_invalid_study_date(self, tmp_path):
        dcm_path = create_test_dicom(tmp_path, study_date="bad")
        data = DicomTagExtractor.extract_tags(dcm_path)
        assert data is None

    def test_malformed_file(self, tmp_path):
        bad_file = tmp_path / "bad.dcm"
        bad_file.write_bytes(b"not a dicom file")
        data = DicomTagExtractor.extract_tags(bad_file)
        assert data is None

    def test_nonexistent_file(self, tmp_path):
        data = DicomTagExtractor.extract_tags(tmp_path / "nonexistent.dcm")
        assert data is None

    def test_optional_tags_missing(self, tmp_path):
        dcm_path = create_test_dicom(
            tmp_path,
            referring_physician="",
            study_description="",
            series_description="",
        )
        data = DicomTagExtractor.extract_tags(dcm_path)
        assert data is not None
        assert data.referring_physician is None
        assert data.study_description is None
        assert data.series_description is None
