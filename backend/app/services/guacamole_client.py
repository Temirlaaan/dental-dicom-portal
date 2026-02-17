"""
Guacamole REST API client for dynamic RDP connection management.

This module provides an async client for Apache Guacamole's REST API,
enabling programmatic creation and deletion of RDP connections without
direct SQL access to Guacamole's database schema.
"""

import httpx

from app.core.config import settings


class GuacamoleClient:
    """
    Async client for Apache Guacamole REST API.

    Manages RDP connections programmatically:
    - Authenticate and retrieve admin token
    - Create RDP connections with optimized parameters
    - Generate user tokens for client URLs
    - Delete connections on cleanup
    """

    def __init__(self):
        self.base_url = settings.GUACAMOLE_URL
        self.admin_user = settings.GUACAMOLE_ADMIN_USER
        self.admin_password = settings.GUACAMOLE_ADMIN_PASSWORD
        self._admin_token: str | None = None

    async def _get_admin_token(self) -> str:
        """
        Authenticate with Guacamole and retrieve admin token.

        Returns:
            authToken (str): Admin authentication token

        Raises:
            httpx.HTTPStatusError: If authentication fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/tokens",
                data={
                    "username": self.admin_user,
                    "password": self.admin_password,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["authToken"]

    async def create_rdp_connection(
        self,
        connection_name: str,
        rdp_hostname: str,
        rdp_port: int,
        rdp_username: str,
        rdp_password: str,
    ) -> str:
        """
        Create an RDP connection in Guacamole.

        Args:
            connection_name: Display name for the connection
            rdp_hostname: Windows Server hostname or IP address
            rdp_port: RDP port (typically 3389)
            rdp_username: Windows username for RDP authentication
            rdp_password: Windows password for RDP authentication

        Returns:
            connection_id (str): Guacamole connection identifier

        Raises:
            httpx.HTTPStatusError: If connection creation fails
        """
        if not self._admin_token:
            self._admin_token = await self._get_admin_token()

        connection_data = {
            "parentIdentifier": "ROOT",
            "name": connection_name,
            "protocol": "rdp",
            "parameters": {
                "hostname": rdp_hostname,
                "port": str(rdp_port),
                "username": rdp_username,
                "password": rdp_password,
                "security": "rdp",
                "ignore-cert": "true",
                # Performance optimizations: disable visual effects
                "enable-wallpaper": "false",
                "enable-theming": "false",
                "enable-font-smoothing": "false",
                "enable-full-window-drag": "false",
                "enable-desktop-composition": "false",
                "enable-menu-animations": "false",
            },
            "attributes": {},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/session/data/mysql/connections",
                headers={"Guacamole-Token": self._admin_token},
                json=connection_data,
            )
            response.raise_for_status()
            data = response.json()
            return data["identifier"]

    async def delete_connection(self, connection_id: str) -> None:
        """
        Delete a Guacamole connection.

        Args:
            connection_id: Guacamole connection identifier to delete

        Raises:
            httpx.HTTPStatusError: If deletion fails
        """
        if not self._admin_token:
            self._admin_token = await self._get_admin_token()

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/session/data/mysql/connections/{connection_id}",
                headers={"Guacamole-Token": self._admin_token},
            )
            response.raise_for_status()

    async def generate_client_token(
        self,
        connection_id: str,
        username: str = "guest",
    ) -> str:
        """
        Generate a temporary auth token for client access.

        Args:
            connection_id: Guacamole connection identifier
            username: Username for token (used for logging)

        Returns:
            token (str): Authentication token for Guacamole client

        Note:
            Currently returns admin token for single-user demo mode.
            In production, this should be enhanced with user-specific token
            generation via Guacamole API or Keycloak integration.
        """
        # TODO: Implement proper user token generation via Guacamole API
        # For now, return admin token (single-user demo mode)
        if not self._admin_token:
            self._admin_token = await self._get_admin_token()

        return self._admin_token

    def build_client_url(self, connection_id: str, token: str) -> str:
        """
        Build Guacamole client URL with authentication token.

        Args:
            connection_id: Guacamole connection identifier
            token: Authentication token

        Returns:
            url (str): Full Guacamole client URL with token parameter
        """
        return f"{self.base_url}/#/client/{connection_id}?token={token}"


async def get_guacamole_client() -> GuacamoleClient:
    """
    Factory function for Guacamole client dependency injection.

    Returns:
        GuacamoleClient instance
    """
    return GuacamoleClient()
