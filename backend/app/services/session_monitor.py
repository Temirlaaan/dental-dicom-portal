import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.audit import AuditLog
from app.models.session import Session
from app.services.guacamole_client import GuacamoleClient

logger = logging.getLogger(__name__)


async def _log_audit(action_type: str, session_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        db.add(AuditLog(
            action_type=action_type,
            resource_type="sessions",
            resource_id=str(session_id),
            details={"source": "session_monitor"},
        ))
        await db.commit()


async def session_timeout_monitor() -> None:
    """
    Runs every SESSION_CHECK_INTERVAL seconds.
    - Hard timeout (SESSION_HARD_TIMEOUT): terminates session and cleans up Guacamole connection.
    - Idle timeout (SESSION_IDLE_TIMEOUT): sets status to 'idle_warning'.
    """
    logger.info("Session timeout monitor started")
    guacamole_client = GuacamoleClient()

    while True:
        try:
            await asyncio.sleep(settings.SESSION_CHECK_INTERVAL)
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            async with async_session_factory() as db:
                result = await db.execute(
                    select(Session).where(
                        Session.status.in_(["active", "idle_warning"]),
                        Session.ended_at.is_(None),
                    )
                )
                sessions = result.scalars().all()

            for s in sessions:
                started = s.started_at.replace(tzinfo=None) if s.started_at.tzinfo else s.started_at
                last_active = s.last_activity_at or s.started_at
                last_active = last_active.replace(tzinfo=None) if last_active.tzinfo else last_active

                total_seconds = (now - started).total_seconds()
                idle_seconds = (now - last_active).total_seconds()

                if total_seconds >= settings.SESSION_HARD_TIMEOUT:
                    # Cleanup Guacamole connection if exists
                    if s.guacamole_connection_id:
                        try:
                            await guacamole_client.delete_connection(s.guacamole_connection_id)
                        except Exception as e:
                            logger.warning("Guacamole cleanup failed for session %s: %s", s.id, e)

                    async with async_session_factory() as db:
                        session_row = await db.get(Session, s.id)
                        if session_row and session_row.ended_at is None:
                            session_row.status = "terminated"
                            session_row.ended_at = now
                            await db.commit()
                    await _log_audit("session_terminated", s.id)
                    logger.info("Session %s hard-terminated (%.0fs elapsed)", s.id, total_seconds)

                elif idle_seconds >= settings.SESSION_IDLE_TIMEOUT and s.status != "idle_warning":
                    async with async_session_factory() as db:
                        session_row = await db.get(Session, s.id)
                        if session_row and session_row.status == "active":
                            session_row.status = "idle_warning"
                            await db.commit()
                    await _log_audit("session_idle_warning", s.id)
                    logger.info("Session %s marked idle_warning (%.0fs idle)", s.id, idle_seconds)

        except asyncio.CancelledError:
            logger.info("Session timeout monitor cancelled")
            return
        except Exception:
            logger.exception("Error in session timeout monitor — will retry")


async def orphaned_session_cleanup() -> None:
    """
    Runs every hour.
    Terminates sessions that are still 'active'/'idle_warning' but started
    more than 2× the hard timeout ago (clearly orphaned).
    Also cleans up their Guacamole connections.
    """
    logger.info("Orphaned session cleanup started")
    guacamole_client = GuacamoleClient()

    while True:
        try:
            await asyncio.sleep(3600)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            cutoff_seconds = settings.SESSION_HARD_TIMEOUT * 2

            async with async_session_factory() as db:
                result = await db.execute(
                    select(Session).where(
                        Session.status.in_(["active", "idle_warning"]),
                        Session.ended_at.is_(None),
                    )
                )
                sessions = result.scalars().all()

            for s in sessions:
                started = s.started_at.replace(tzinfo=None) if s.started_at.tzinfo else s.started_at
                if (now - started).total_seconds() >= cutoff_seconds:
                    # Cleanup Guacamole connection if exists
                    if s.guacamole_connection_id:
                        try:
                            await guacamole_client.delete_connection(s.guacamole_connection_id)
                        except Exception as e:
                            logger.warning("Guacamole cleanup failed for orphaned session %s: %s", s.id, e)

                    async with async_session_factory() as db:
                        session_row = await db.get(Session, s.id)
                        if session_row and session_row.ended_at is None:
                            session_row.status = "terminated"
                            session_row.ended_at = now
                            await db.commit()
                    await _log_audit("session_orphan_cleanup", s.id)
                    logger.info("Orphaned session %s terminated", s.id)

        except asyncio.CancelledError:
            logger.info("Orphaned session cleanup cancelled")
            return
        except Exception:
            logger.exception("Error in orphaned session cleanup — will retry")
