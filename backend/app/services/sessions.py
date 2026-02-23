"""
Session orchestration service.

Handles session lifecycle: creation, termination, extension, and listing.
Enforces concurrency limits (per-doctor and global) and manages the VM pool
using the "1 VM = 1 doctor" model.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import CurrentUser
from app.models import Session, VMInstance
from app.services.guacamole_client import GuacamoleClient
from app.services.winrm_client import WinRMClient

logger = logging.getLogger(__name__)


async def create_session(
    db: AsyncSession,
    doctor_id: uuid.UUID,
    patient_id: uuid.UUID,
    winrm_client: WinRMClient,
    guacamole_client: GuacamoleClient,
) -> Session:
    """
    Create a new session with a dedicated VM from the pool.

    Steps:
    1. Check per-doctor and global concurrency limits
    2. Find a free VM (status="ready") from the pool
    3. Mark VM as "assigned" and bind to doctor
    4. Mount SMB share via WinRM
    5. Create Guacamole RDP connection to the VM's IP
    6. Launch DTX Studio via WinRM
    7. On failure — rollback: cleanup VM and return to pool
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

    # Find a free VM from the pool
    vm_result = await db.execute(
        select(VMInstance).where(VMInstance.status == "ready").limit(1)
    )
    vm = vm_result.scalar_one_or_none()
    if not vm:
        raise HTTPException(
            status_code=503,
            detail="No available VMs in the pool. All VMs are currently in use.",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Create session record with status="creating"
    session = Session(
        doctor_id=doctor_id,
        patient_id=patient_id,
        vm_instance_id=vm.id,
        vm_ip=vm.ip_address,
        status="creating",
        started_at=now,
    )
    db.add(session)

    # Mark VM as assigned
    vm.status = "assigned"
    vm.doctor_id = doctor_id
    vm.session_id = session.id
    vm.assigned_at = now

    await db.commit()
    await db.refresh(session)

    try:
        # Step 1: Mount SMB share via WinRM
        doctor_id_str = str(doctor_id).replace("-", "")[:16]
        share_name = f"svc_{doctor_id_str}"
        mount_result = await winrm_client.mount_smb_share(
            vm_ip=vm.ip_address,
            doctor_id=doctor_id_str,
            drive_letter=settings.SMB_MOUNT_DRIVE,
        )
        logger.info("SMB mount on %s: %s", vm.ip_address, mount_result)

        vm.mounted_share = settings.SMB_MOUNT_DRIVE
        await db.commit()

        # Step 2: Create Guacamole RDP connection to this specific VM
        connection_name = f"session_{session.id}"
        guacamole_connection_id = await guacamole_client.create_rdp_connection(
            connection_name=connection_name,
            rdp_hostname=vm.ip_address,
            rdp_port=vm.rdp_port,
            rdp_username=settings.VM_DEFAULT_RDP_USER,
            rdp_password=settings.VM_DEFAULT_RDP_PASSWORD,
        )

        # Step 3: Launch DTX Studio on the VM
        dicom_path = f"{settings.SMB_MOUNT_DRIVE}\\inbox"
        await winrm_client.launch_dtx_studio(
            vm_ip=vm.ip_address,
            dicom_path=dicom_path,
        )

        # Success: update session to active
        session.guacamole_connection_id = guacamole_connection_id
        session.windows_user = settings.VM_DEFAULT_RDP_USER
        session.status = "active"
        session.last_activity_at = now
        await db.commit()
        await db.refresh(session)

        return session

    except Exception as e:
        logger.error("Session creation failed for VM %s: %s", vm.ip_address, e)

        # Rollback: cleanup Guacamole connection
        if session.guacamole_connection_id:
            try:
                await guacamole_client.delete_connection(session.guacamole_connection_id)
            except Exception:
                pass

        # Rollback: cleanup VM session (DTX + SMB)
        try:
            await winrm_client.cleanup_vm_session(vm.ip_address)
        except Exception:
            pass

        # Return VM to pool
        vm.status = "ready"
        vm.doctor_id = None
        vm.doctor_name = None
        vm.session_id = None
        vm.mounted_share = None
        vm.assigned_at = None

        # Mark session as terminated
        session.status = "terminated"
        session.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}",
        )


async def _release_vm(db: AsyncSession, vm_instance_id: uuid.UUID | None) -> None:
    """Release a VM back to the pool."""
    if not vm_instance_id:
        return
    vm = await db.get(VMInstance, vm_instance_id)
    if vm and vm.status == "assigned":
        vm.status = "ready"
        vm.doctor_id = None
        vm.doctor_name = None
        vm.session_id = None
        vm.mounted_share = None
        vm.assigned_at = None


async def end_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    winrm_client: WinRMClient,
    guacamole_client: GuacamoleClient,
) -> None:
    """
    Terminate an active session, cleanup all resources, and release VM back to pool.
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
            logger.warning("Guacamole cleanup failed for session %s: %s", session_id, e)

    # Cleanup VM session (DTX + SMB) via WinRM
    if session.vm_ip:
        try:
            await winrm_client.cleanup_vm_session(session.vm_ip)
        except Exception as e:
            logger.warning("VM cleanup failed for session %s on %s: %s", session_id, session.vm_ip, e)

    # Release VM back to pool
    await _release_vm(db, session.vm_instance_id)

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
    """
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status not in ["active", "idle_warning"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot extend session in status '{session.status}'",
        )

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
    Admins see all sessions. Doctors see only their own sessions.
    """
    query = select(Session).order_by(Session.started_at.desc())

    if not current_user.is_admin:
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
