"""
Session orchestration service.

Handles session lifecycle: creation, termination, extension, and listing.
Enforces concurrency limits (per-doctor and global) and manages WinRM operations.
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.models import Session
from app.services.winrm_client import WinRMClient
from app.services.guacamole_client import GuacamoleClient
from app.core.config import settings


async def create_session(
    db: AsyncSession,
    doctor_id: uuid.UUID,
    patient_id: uuid.UUID,
    winrm_client: WinRMClient,
    guacamole_client: GuacamoleClient,
) -> Session:
    """
    Create a new RDS session with Guacamole RDP connection.

    Enforces concurrency limits:
    - Per-doctor limit: 1 active session
    - Global limit: MAX_CONCURRENT_SESSIONS (default 5)

    Creates session in database, provisions RDS session via WinRM,
    creates Guacamole RDP connection, launches DTX Studio, and updates session status.

    On failure, attempts cleanup of both WinRM and Guacamole resources.

    Args:
        db: Database session
        doctor_id: UUID of the doctor
        patient_id: UUID of the patient
        winrm_client: WinRM client for remote operations
        guacamole_client: Guacamole client for RDP connection management

    Returns:
        Created Session object

    Raises:
        HTTPException: 409 if doctor already has active session
        HTTPException: 429 if global session limit reached
        HTTPException: 500 if session creation fails
    """
    # Check per-doctor limit (only 1 active session per doctor)
    existing_result = await db.execute(
        select(Session).where(
            Session.doctor_id == doctor_id,
            Session.status.in_(["creating", "active", "idle_warning"]),
            Session.ended_at.is_(None),
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Doctor already has an active session. End it before creating a new one.",
        )

    # Check global concurrent session limit
    count_result = await db.execute(
        select(func.count()).select_from(Session).where(
            Session.status.in_(["creating", "active", "idle_warning"]),
            Session.ended_at.is_(None),
        )
    )
    active_count = count_result.scalar()
    if active_count >= settings.MAX_CONCURRENT_SESSIONS:
        raise HTTPException(
            status_code=429,
            detail=f"Session limit reached ({settings.MAX_CONCURRENT_SESSIONS} concurrent sessions). Try again later.",
        )

    # Create session record with status="creating"
    session = Session(
        doctor_id=doctor_id,
        patient_id=patient_id,
        status="creating",
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    try:
        # Step 1: Create RDS session via WinRM
        windows_user = f"dtx_user_{session.id.hex[:8]}"
        rds_session_id = await winrm_client.run_script(
            "create-rds-session.ps1",
            {
                "UserName": windows_user,
                "PatientId": str(patient_id),
            },
        )

        # Step 2: Create Guacamole RDP connection
        connection_name = f"session_{session.id}"
        guacamole_connection_id = await guacamole_client.create_rdp_connection(
            connection_name=connection_name,
            rdp_hostname=settings.WINDOWS_RDP_HOST,
            rdp_port=settings.WINDOWS_RDP_PORT,
            rdp_username=windows_user,
            rdp_password=settings.WINDOWS_RDP_PASSWORD,
        )

        # Step 3: Launch DTX Studio in the RDS session
        await winrm_client.run_script(
            "launch-dtx-studio.ps1",
            {
                "SessionId": rds_session_id,
                "DicomPath": f"\\\\shared\\dicom\\patients\\{patient_id}",
            },
        )

        # Success: update session to active
        session.rds_session_id = rds_session_id
        session.guacamole_connection_id = guacamole_connection_id
        session.windows_user = windows_user
        session.status = "active"
        session.last_activity_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        await db.refresh(session)

        return session

    except Exception as e:
        # Rollback: cleanup partial resources
        try:
            if session.guacamole_connection_id:
                await guacamole_client.delete_connection(session.guacamole_connection_id)
        except Exception:
            # Best-effort cleanup
            pass

        try:
            if session.rds_session_id:
                await winrm_client.run_script(
                    "cleanup-session.ps1",
                    {"SessionId": session.rds_session_id},
                )
        except Exception:
            # Best-effort cleanup
            pass

        # Mark session as terminated
        session.status = "terminated"
        session.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}",
        )


async def end_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    winrm_client: WinRMClient,
    guacamole_client: GuacamoleClient,
) -> None:
    """
    Terminate an active session and cleanup all resources.

    Runs cleanup script via WinRM, deletes Guacamole connection,
    and updates session status to terminated.

    Args:
        db: Database session
        session_id: UUID of the session to terminate
        winrm_client: WinRM client for remote operations
        guacamole_client: Guacamole client for connection cleanup

    Raises:
        HTTPException: 404 if session not found
        HTTPException: 400 if session already terminated
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "terminated":
        raise HTTPException(status_code=400, detail="Session already terminated")

    # Cleanup Guacamole connection
    if session.guacamole_connection_id:
        try:
            await guacamole_client.delete_connection(session.guacamole_connection_id)
        except Exception as e:
            print(f"Warning: Guacamole cleanup failed for session {session_id}: {e}")

    # Cleanup RDS session if it was created
    if session.rds_session_id:
        try:
            await winrm_client.run_script(
                "cleanup-session.ps1",
                {"SessionId": session.rds_session_id},
            )
        except Exception as e:
            print(f"Warning: WinRM cleanup failed for session {session_id}: {e}")

    # Update session status
    session.status = "terminated"
    session.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()


async def extend_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> Session:
    """
    Extend a session by updating last_activity_at.

    Resets idle warning status back to active if applicable.

    Args:
        db: Database session
        session_id: UUID of the session to extend

    Returns:
        Updated Session object

    Raises:
        HTTPException: 404 if session not found
        HTTPException: 400 if session not in extendable state
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status not in ["active", "idle_warning"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot extend session in status '{session.status}'",
        )

    # Update activity timestamp and reset to active if needed
    session.last_activity_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if session.status == "idle_warning":
        session.status = "active"

    await db.commit()
    await db.refresh(session)

    return session


async def list_sessions(
    db: AsyncSession,
    current_user: CurrentUser,
) -> list[Session]:
    """
    List sessions based on user role.

    Admins see all sessions.
    Doctors see only their own sessions.

    Args:
        db: Database session
        current_user: Authenticated user context

    Returns:
        List of Session objects
    """
    query = select(Session).order_by(Session.started_at.desc())

    if not current_user.is_admin:
        # Doctors see only their own sessions
        # Need to join with Doctor to filter by keycloak_user_id
        from app.models import Doctor

        doctor_result = await db.execute(
            select(Doctor).where(Doctor.keycloak_user_id == current_user.id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            return []

        query = query.where(Session.doctor_id == doctor.id)

    result = await db.execute(query)
    return list(result.scalars().all())
