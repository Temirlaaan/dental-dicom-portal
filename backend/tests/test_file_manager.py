from pathlib import Path

from app.services.file_manager import move_to_error, move_to_processed


class TestMoveToProcessed:
    def test_move_file(self, tmp_path):
        src = tmp_path / "input" / "test.dcm"
        src.parent.mkdir()
        src.write_text("data")
        dest_dir = str(tmp_path / "processed")

        result = move_to_processed(src, dest_dir)

        assert result is not None
        assert result.exists()
        assert result.name == "test.dcm"
        assert not src.exists()

    def test_empty_dir_returns_none(self, tmp_path):
        src = tmp_path / "test.dcm"
        src.write_text("data")
        result = move_to_processed(src, "")
        assert result is None
        assert src.exists()

    def test_conflict_resolution(self, tmp_path):
        dest_dir = tmp_path / "processed"
        dest_dir.mkdir()

        # Create a file that already exists in dest
        (dest_dir / "test.dcm").write_text("old")

        src = tmp_path / "input" / "test.dcm"
        src.parent.mkdir()
        src.write_text("new")

        result = move_to_processed(src, str(dest_dir))
        assert result is not None
        assert result.name == "test_1.dcm"
        assert result.read_text() == "new"


class TestMoveToError:
    def test_move_file(self, tmp_path):
        src = tmp_path / "test.dcm"
        src.write_text("bad data")
        dest_dir = str(tmp_path / "error")

        result = move_to_error(src, dest_dir)

        assert result is not None
        assert result.exists()
        assert not src.exists()

    def test_creates_directory(self, tmp_path):
        src = tmp_path / "test.dcm"
        src.write_text("data")
        dest_dir = str(tmp_path / "deep" / "nested" / "error")

        result = move_to_error(src, dest_dir)
        assert result is not None
        assert Path(dest_dir).is_dir()
