"""
WinRM client service with mockable abstraction for testing.

This module provides a Protocol-based abstraction for WinRM operations,
allowing dependency injection of either a real WinRM client (for production)
or a mock client (for CI/testing without Windows Server).
"""

import asyncio
from typing import Protocol, runtime_checkable

from app.core.config import settings


@runtime_checkable
class WinRMClient(Protocol):
    """Protocol for WinRM client abstraction."""

    async def run_script(self, script_path: str, args: dict[str, str]) -> str:
        """
        Execute a PowerShell script via WinRM.

        Args:
            script_path: Path to the PowerShell script relative to backend/scripts/
            args: Dictionary of named arguments to pass to the script

        Returns:
            Script stdout output
        """
        ...


class RealWinRMClient:
    """Real WinRM client using pywinrm for production use."""

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password

    async def run_script(self, script_path: str, args: dict[str, str]) -> str:
        """Execute PowerShell script via WinRM."""
        # Import here to avoid dependency issues in tests
        import winrm

        # Build PowerShell command
        script_args = " ".join([f"-{k} '{v}'" for k, v in args.items()])
        ps_command = f"powershell.exe -ExecutionPolicy Bypass -File C:\\DentalPortal\\scripts\\{script_path} {script_args}"

        # Run in thread pool to avoid blocking async event loop
        def _run_sync():
            session = winrm.Session(
                f"https://{self.host}:5986/wsman",
                auth=(self.username, self.password),
                transport="ntlm",
                server_cert_validation="ignore",
            )
            result = session.run_cmd(ps_command)
            if result.status_code != 0:
                raise RuntimeError(f"WinRM script failed: {result.std_err.decode('utf-8')}")
            return result.std_out.decode("utf-8").strip()

        return await asyncio.to_thread(_run_sync)


class MockWinRMClient:
    """Mock WinRM client for testing without Windows Server."""

    def __init__(self):
        self._session_counter = 0

    async def run_script(self, script_path: str, args: dict[str, str]) -> str:
        """Simulate PowerShell script execution."""
        await asyncio.sleep(0.1)  # Simulate network delay

        if "create-rds-session" in script_path:
            self._session_counter += 1
            return f"RDS-SESSION-{self._session_counter:05d}"

        elif "launch-dtx-studio" in script_path:
            return "PID-12345"

        elif "cleanup-session" in script_path:
            return "OK"

        return ""


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
