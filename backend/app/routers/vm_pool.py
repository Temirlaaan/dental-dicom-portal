"""VM Pool management endpoints (admin only)."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.models.vm_instance import VMInstance
from app.services.winrm_client import WinRMClient, get_winrm_client

router = APIRouter(dependencies=[Depends(require_role("admin"))])


class VMCreateRequest(BaseModel):
    hostname: str
    ip_address: str
    rdp_port: int = 3389
    winrm_port: int = 5985


class VMResponse(BaseModel):
    id: uuid.UUID
    hostname: str
    ip_address: str
    rdp_port: int
    winrm_port: int
    status: str
    doctor_id: uuid.UUID | None
    doctor_name: str | None
    session_id: uuid.UUID | None
    mounted_share: str | None
    assigned_at: datetime | None
    last_health_check: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[VMResponse])
async def list_vms(db: AsyncSession = Depends(get_db)):
    """List all VMs in the pool."""
    result = await db.execute(select(VMInstance).order_by(VMInstance.hostname))
    return list(result.scalars().all())


@router.post("", response_model=VMResponse, status_code=201)
async def register_vm(
    request: VMCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new VM in the pool."""
    vm = VMInstance(
        hostname=request.hostname,
        ip_address=request.ip_address,
        rdp_port=request.rdp_port,
        winrm_port=request.winrm_port,
        status="ready",
    )
    db.add(vm)
    await db.commit()
    await db.refresh(vm)
    return vm


@router.delete("/{vm_id}", status_code=204)
async def delete_vm(
    vm_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a VM from the pool (only if not assigned)."""
    vm = await db.get(VMInstance, vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    if vm.status == "assigned":
        raise HTTPException(status_code=409, detail="Cannot delete VM while it is assigned to a session")
    await db.delete(vm)
    await db.commit()


@router.post("/{vm_id}/health-check", response_model=VMResponse)
async def health_check_vm(
    vm_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    winrm_client: WinRMClient = Depends(get_winrm_client),
):
    """Check VM health via WinRM."""
    vm = await db.get(VMInstance, vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")

    healthy = await winrm_client.check_vm_health(vm.ip_address)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    vm.last_health_check = now

    if not healthy and vm.status == "ready":
        vm.status = "offline"
    elif healthy and vm.status == "offline":
        vm.status = "ready"

    await db.commit()
    await db.refresh(vm)
    return vm


@router.post("/{vm_id}/force-release", response_model=VMResponse)
async def force_release_vm(
    vm_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    winrm_client: WinRMClient = Depends(get_winrm_client),
):
    """Force-release a stuck VM back to the pool."""
    vm = await db.get(VMInstance, vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")

    if vm.status != "assigned":
        raise HTTPException(status_code=400, detail=f"VM is not assigned (status: {vm.status})")

    # Attempt WinRM cleanup
    try:
        await winrm_client.cleanup_vm_session(vm.ip_address)
    except Exception:
        pass  # Best-effort cleanup

    vm.status = "ready"
    vm.doctor_id = None
    vm.doctor_name = None
    vm.session_id = None
    vm.mounted_share = None
    vm.assigned_at = None

    await db.commit()
    await db.refresh(vm)
    return vm
