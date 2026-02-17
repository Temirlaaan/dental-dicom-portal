import logging
import time
from collections import OrderedDict
from pathlib import Path
from threading import Lock

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.core.config import settings
from app.services.dicom_ingestion import DicomIngestionService
from app.services.dicom_parser import DicomTagExtractor
from app.services.file_manager import move_to_error, move_to_processed

logger = logging.getLogger(__name__)

# How long to wait for a file write to complete (seconds)
WRITE_SETTLE_DELAY = 0.2

# Maximum number of recent files to track for deduplication
MAX_RECENT_FILES = 500

# Minimum seconds before re-processing the same file path
DEDUP_WINDOW = 2.0


class DicomFileHandler(FileSystemEventHandler):

    def __init__(self, ingestion_service: DicomIngestionService):
        super().__init__()
        self._ingestion = ingestion_service
        self._recent: OrderedDict[str, float] = OrderedDict()
        self._lock = Lock()

    def _is_duplicate_event(self, path: str) -> bool:
        """Check if we've recently processed this file path."""
        now = time.monotonic()
        with self._lock:
            last_seen = self._recent.get(path)
            if last_seen is not None and (now - last_seen) < DEDUP_WINDOW:
                return True
            self._recent[path] = now
            # Trim old entries
            while len(self._recent) > MAX_RECENT_FILES:
                self._recent.popitem(last=False)
        return False

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() != ".dcm":
            return

        if self._is_duplicate_event(event.src_path):
            logger.debug("Skipping duplicate event for %s", event.src_path)
            return

        # Wait for the file write to complete
        time.sleep(WRITE_SETTLE_DELAY)

        self._process_file(file_path)

    def _process_file(self, file_path: Path):
        logger.info("Processing DICOM file: %s", file_path)

        # Extract tags
        data = DicomTagExtractor.extract_tags(file_path)
        if data is None:
            logger.warning("Failed to extract tags, moving to error: %s", file_path)
            move_to_error(file_path, settings.DICOM_ERROR_DIR)
            return

        # Ingest into database
        try:
            created = self._ingestion.ingest_dicom(data, str(file_path))
        except Exception:
            logger.exception("Database error ingesting %s", file_path)
            move_to_error(file_path, settings.DICOM_ERROR_DIR)
            return

        if created:
            move_to_processed(file_path, settings.DICOM_PROCESSED_DIR)
        else:
            # Duplicate — still move to processed if configured
            move_to_processed(file_path, settings.DICOM_PROCESSED_DIR)


def run_watcher(ingestion_service: DicomIngestionService) -> Observer:
    """Create and start the watchdog Observer. Returns the observer for shutdown control."""
    watch_dir = settings.DICOM_WATCH_DIR
    Path(watch_dir).mkdir(parents=True, exist_ok=True)

    handler = DicomFileHandler(ingestion_service)
    observer = Observer()
    observer.schedule(handler, watch_dir, recursive=False)
    observer.start()

    logger.info("DICOM watcher started on: %s", watch_dir)
    return observer
