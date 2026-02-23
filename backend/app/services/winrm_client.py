"""
WinRM client service with mockable abstraction for testing.

This module provides a Protocol-based abstraction for WinRM operations,
allowing dependency injection of either a real WinRM client (for production)
or a mock client (for CI/testing without Windows Server).

Supports both the legacy run_script interface and the new per-VM methods
for the "1 VM = 1 doctor" model.
"""

import asyncio
import logging
from typing import Protocol, runtime_checkable

from app.core.config import settings

logger = logging.getLogger(__name__)


@runtime_checkable
class WinRMClient(Protocol):
    """Protocol for WinRM client abstraction."""

    async def run_script(self, script_path: str, args: dict[str, str]) -> str: ...

    async def run_command_on_vm(self, vm_ip: str, command: str) -> str: ...

    async def mount_smb_share(self, vm_ip: str, doctor_id: str, drive_letter: str = "Z:") -> str: ...

    async def unmount_smb_share(self, vm_ip: str, drive_letter: str = "Z:") -> str: ...

    async def launch_dtx_studio(self, vm_ip: str, dicom_path: str = "") -> str: ...

    async def check_vm_health(self, vm_ip: str) -> bool: ...

    async def cleanup_vm_session(self, vm_ip: str) -> str: ...


class RealWinRMClient:
    """Real WinRM client using pywinrm for production use."""

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password

    def _create_session(self, target_host: str):
        import winrm
        return winrm.Session(
            f"http://{target_host}:5985/wsman",
            auth=(self.username, self.password),
            transport="ntlm",
        )

    async def run_script(self, script_path: str, args: dict[str, str]) -> str:
        """Execute PowerShell script via WinRM (legacy interface)."""
        script_args = " ".join([f"-{k} '{v}'" for k, v in args.items()])
        ps_command = f"powershell.exe -ExecutionPolicy Bypass -File C:\\DentalPortal\\scripts\\{script_path} {script_args}"

        def _run_sync():
            session = self._create_session(self.host)
            result = session.run_cmd(ps_command)
            if result.status_code != 0:
                raise RuntimeError(f"WinRM script failed: {result.std_err.decode('utf-8')}")
            return result.std_out.decode("utf-8").strip()

        return await asyncio.to_thread(_run_sync)

    async def run_command_on_vm(self, vm_ip: str, command: str) -> str:
        """Execute a PowerShell command on a specific VM."""
        def _run_sync():
            session = self._create_session(vm_ip)
            result = session.run_ps(command)
            if result.status_code != 0:
                stderr = result.std_err.decode("utf-8")
                raise RuntimeError(f"WinRM command failed on {vm_ip}: {stderr}")
            return result.std_out.decode("utf-8").strip()

        return await asyncio.to_thread(_run_sync)

    async def mount_smb_share(self, vm_ip: str, doctor_id: str, drive_letter: str = "Z:") -> str:
        """Mount an SMB share on a VM for a specific doctor.

        Uses cmd.exe with /persistent:yes so the drive persists across WinRM sessions.
        Removes any existing mapping on the drive letter first.
        """
        smb_user = f"{settings.SMB_SERVICE_USER_PREFIX}{doctor_id}"
        smb_password = settings.SMB_SERVICE_PASSWORD
        smb_path = f"\\\\{settings.SMB_SERVER}\\{doctor_id}"
        command = (
            f"net use {drive_letter} /delete /y 2>nul & "
            f"net use {drive_letter} {smb_path} "
            f"/user:{smb_user} {smb_password} /persistent:yes"
        )

        def _run_sync():
            session = self._create_session(vm_ip)
            result = session.run_cmd(command)
            if result.status_code != 0:
                stderr = result.std_err.decode("utf-8")
                raise RuntimeError(f"SMB mount failed on {vm_ip}: {stderr}")
            return result.std_out.decode("utf-8").strip()

        return await asyncio.to_thread(_run_sync)

    async def unmount_smb_share(self, vm_ip: str, drive_letter: str = "Z:") -> str:
        """Unmount an SMB share on a VM."""
        command = f"net use {drive_letter} /delete /y"

        def _run_sync():
            session = self._create_session(vm_ip)
            result = session.run_cmd(command)
            return result.std_out.decode("utf-8").strip()

        return await asyncio.to_thread(_run_sync)

    async def launch_dtx_studio(self, vm_ip: str, dicom_path: str = "") -> str:
        """Launch DTX Studio on a VM."""
        ps_command = (
            '$dtxPath = "C:\\Program Files\\DTX Studio\\DTXStudio.exe"; '
            'if (Test-Path $dtxPath) { '
            f'  Start-Process -FilePath $dtxPath -ArgumentList "{dicom_path}"; '
            '  Write-Output "DTX Studio launched" '
            '} else { '
            '  Write-Output "DTX Studio not found at $dtxPath" '
            '}'
        )
        return await self.run_command_on_vm(vm_ip, ps_command)

    async def check_vm_health(self, vm_ip: str) -> bool:
        """Check if a VM is reachable via WinRM."""
        try:
            result = await self.run_command_on_vm(vm_ip, 'Write-Output "OK"')
            return result.strip() == "OK"
        except Exception as e:
            logger.warning("Health check failed for VM %s: %s", vm_ip, e)
            return False

    async def cleanup_vm_session(self, vm_ip: str) -> str:
        """Close DTX Studio and unmount SMB share on a VM."""
        ps_command = (
            'Get-Process -Name "DTXStudio*" -ErrorAction SilentlyContinue | Stop-Process -Force; '
            'Write-Output "DTX processes stopped"'
        )
        try:
            await self.run_command_on_vm(vm_ip, ps_command)
        except Exception as e:
            logger.warning("DTX cleanup failed on %s: %s", vm_ip, e)

        try:
            await self.unmount_smb_share(vm_ip)
        except Exception as e:
            logger.warning("SMB unmount failed on %s: %s", vm_ip, e)

        return "cleanup_complete"


class MockWinRMClient:
    """Mock WinRM client for testing without Windows Server."""

    def __init__(self):
        self._session_counter = 0

    async def run_script(self, script_path: str, args: dict[str, str]) -> str:
        """Simulate PowerShell script execution."""
        await asyncio.sleep(0.1)

        if "create-rds-session" in script_path:
            self._session_counter += 1
            return f"RDS-SESSION-{self._session_counter:05d}"
        elif "launch-dtx-studio" in script_path:
            return "PID-12345"
        elif "cleanup-session" in script_path:
            return "OK"
        return ""

    async def run_command_on_vm(self, vm_ip: str, command: str) -> str:
        await asyncio.sleep(0.1)
        return "mock_output"

    async def mount_smb_share(self, vm_ip: str, doctor_id: str, drive_letter: str = "Z:") -> str:
        await asyncio.sleep(0.1)
        return f"Mock: mounted {drive_letter} for {doctor_id} on {vm_ip}"

    async def unmount_smb_share(self, vm_ip: str, drive_letter: str = "Z:") -> str:
        await asyncio.sleep(0.1)
        return f"Mock: unmounted {drive_letter} on {vm_ip}"

    async def launch_dtx_studio(self, vm_ip: str, dicom_path: str = "") -> str:
        await asyncio.sleep(0.1)
        return "Mock: DTX Studio launched"

    async def check_vm_health(self, vm_ip: str) -> bool:
        await asyncio.sleep(0.1)
        return True

    async def cleanup_vm_session(self, vm_ip: str) -> str:
        await asyncio.sleep(0.1)
        return "mock_cleanup_complete"


async def get_winrm_client() -> WinRMClient:
    """
    Factory function for WinRM client dependency injection.

    Returns MockWinRMClient if WINRM_HOST is empty (for testing),
    otherwise returns RealWinRMClient (for production).
    """
    if not settings.WINRM_HOST:
        return MockWinRMClient()

    return RealWinRMClient(
        host=settings.WINRM_HOST,
        username=settings.WINRM_USER,
        password=settings.WINRM_PASSWORD,
    )
