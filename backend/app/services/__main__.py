"""Entry point for the DICOM ingestion service.

Run with: python -m app.services
"""

import logging
import signal
import sys

from sqlalchemy import create_engine

from app.core.config import settings
from app.services.dicom_ingestion import DicomIngestionService
from app.services.dicom_watcher import run_watcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _build_sync_url(async_url: str) -> str:
    """Convert an asyncpg DATABASE_URL to a psycopg2 one."""
    return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)


def main():
    sync_url = _build_sync_url(settings.DATABASE_URL)
    logger.info("Creating sync database engine")
    sync_engine = create_engine(sync_url, pool_pre_ping=True)

    ingestion_service = DicomIngestionService(sync_engine)
    observer = run_watcher(ingestion_service)

    # Graceful shutdown on SIGTERM / SIGINT
    def _shutdown(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        observer.stop()
        observer.join(timeout=5)
        sync_engine.dispose()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("DICOM ingestion service running. Press Ctrl+C to stop.")
    try:
        observer.join()
    except KeyboardInterrupt:
        _shutdown(signal.SIGINT, None)


if __name__ == "__main__":
    main()
