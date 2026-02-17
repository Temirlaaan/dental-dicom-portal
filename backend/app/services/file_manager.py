import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def _move_file(src: Path, dest_dir: Path) -> Path | None:
    """Move a file to dest_dir, handling name conflicts with a numeric suffix."""
    if not dest_dir:
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    # Handle name conflicts
    if dest.exists():
        stem = src.stem
        suffix = src.suffix
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    try:
        shutil.move(str(src), str(dest))
        logger.info("Moved %s -> %s", src, dest)
        return dest
    except OSError:
        logger.exception("Failed to move %s to %s", src, dest_dir)
        return None


def move_to_processed(file_path: Path, processed_dir: str) -> Path | None:
    """Move a successfully processed file to the processed directory."""
    if not processed_dir:
        return None
    return _move_file(file_path, Path(processed_dir))


def move_to_error(file_path: Path, error_dir: str) -> Path | None:
    """Move a failed file to the error directory."""
    if not error_dir:
        return None
    return _move_file(file_path, Path(error_dir))
