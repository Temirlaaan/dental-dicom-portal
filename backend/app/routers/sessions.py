"""Session management API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user, require_role
from app.models import Doctor, Session
from app.schemas.session import SessionCreate, SessionSchema
from app.services import sessions as sessions_service
from app.services.winrm_client import WinRMClient, get_winrm_client
from app.services.guacamole_client import GuacamoleClient, get_guacamole_client

router = APIRouter()


@router.post("", response_model=SessionSchema, status_code=201)
async def create_session(
    req: SessionCreate,
    current_user: Annotated[CurrentUser, Depends(require_role("doctor"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    winrm: Annotated[WinRMClient, Depends(get_winrm_client)],
    guacamole: Annotated[GuacamoleClient, Depends(get_guacamole_client)],
):
    """
    Create a new RDS session with Guacamole RDP connection.

    Provisions a Windows RDS session, creates Guacamole RDP connection,
    launches DTX Studio with patient DICOM data.
    Enforces per-doctor limit (1 active session) and global limit (MAX_CONCURRENT_SESSIONS).

    Requires doctor role.
    """
    # Get doctor record from keycloak_user_id
    from sqlalchemy import select

    doctor_result = await db.execute(
        select(Doctor).where(Doctor.keycloak_user_id == current_user.id)
    )
    doctor = doctor_result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found. Contact administrator.",
        )

    session = await sessions_service.create_session(
        db=db,
        doctor_id=doctor.id,
        patient_id=req.patient_id,
        winrm_client=winrm,
        guacamole_client=guacamole,
    )

    return session


@router.get("", response_model=list[SessionSchema])
async def list_sessions(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    List sessions.

    Admins see all sessions.
    Doctors see only their own sessions.
    """
    sessions = await sessions_service.list_sessions(db, current_user)
    return sessions


@router.get("/{session_id}", response_model=SessionSchema)
async def get_session(
    session_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a single session by ID.

    Doctors can only access their own sessions.
    Admins can access all sessions.
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Access control: doctor sees only their own, admin sees all
    if not current_user.is_admin:
        from sqlalchemy import select

        doctor_result = await db.execute(
            select(Doctor).where(Doctor.keycloak_user_id == current_user.id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or session.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this session",
            )

    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    winrm: Annotated[WinRMClient, Depends(get_winrm_client)],
    guacamole: Annotated[GuacamoleClient, Depends(get_guacamole_client)],
):
    """
    Terminate a session and cleanup all resources.

    Cleans up both WinRM and Guacamole resources.
    Doctors can terminate only their own sessions.
    Admins can terminate any session.
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Access control: only the doctor who owns it or admin can delete
    if not current_user.is_admin:
        from sqlalchemy import select

        doctor_result = await db.execute(
            select(Doctor).where(Doctor.keycloak_user_id == current_user.id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or session.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to terminate this session",
            )

    await sessions_service.end_session(db, session_id, winrm, guacamole)


@router.post("/{session_id}/extend", response_model=SessionSchema)
async def extend_session(
    session_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Extend a session by updating last activity timestamp.

    Resets idle warning status back to active.
    Doctors can extend only their own sessions.
    Admins can extend any session.
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Access control
    if not current_user.is_admin:
        from sqlalchemy import select

        doctor_result = await db.execute(
            select(Doctor).where(Doctor.keycloak_user_id == current_user.id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or session.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to extend this session",
            )

    updated_session = await sessions_service.extend_session(db, session_id)
    return updated_session


@router.get("/{session_id}/guacamole-url")
async def get_guacamole_url(
    session_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    guacamole_client: Annotated[GuacamoleClient, Depends(get_guacamole_client)],
):
    """
    Generate Guacamole client URL for accessing the session.

    Returns a token-based URL that can be embedded in an iframe for
    browser-based RDP access to the Windows Server session.

    Doctors can only access URLs for their own sessions.
    Admins can access URLs for all sessions.

    Returns:
        {"url": "http://domain/guacamole/#/client/{conn_id}?token={token}"}
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Access control
    if not current_user.is_admin:
        from sqlalchemy import select

        doctor_result = await db.execute(
            select(Doctor).where(Doctor.keycloak_user_id == current_user.id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or session.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this session",
            )

    if not session.guacamole_connection_id:
        raise HTTPException(
            status_code=400,
            detail="Session has no Guacamole connection",
        )

    if session.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Session is {session.status}, must be active to access",
        )

    # Generate token and build URL
    token = await guacamole_client.generate_client_token(
        session.guacamole_connection_id,
        username=current_user.username,
    )
    url = guacamole_client.build_client_url(
        session.guacamole_connection_id,
        token,
    )

    return {"url": url}
