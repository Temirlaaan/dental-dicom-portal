from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dental_portal"

    # Keycloak
    KEYCLOAK_URL: str = "http://10.121.245.146:8180"
    KEYCLOAK_REALM: str = "dental-portal"
    KEYCLOAK_CLIENT_ID: str = "dental-backend"
    KEYCLOAK_CLIENT_SECRET: str = "dental-backend-secret"
    KEYCLOAK_FRONTEND_CLIENT_ID: str = "dental-frontend"

    # Guacamole
    GUACAMOLE_URL: str = "http://localhost:8080/guacamole"
    GUACAMOLE_ADMIN_USER: str = "guacadmin"  # Default admin username
    GUACAMOLE_ADMIN_PASSWORD: str = "guacadmin"  # Change in production

    # Windows Server (WinRM)
    WINRM_HOST: str = ""
    WINRM_USER: str = ""
    WINRM_PASSWORD: str = ""

    # Windows RDP Configuration (for Guacamole connections)
    WINDOWS_RDP_HOST: str = ""  # Windows Server hostname/IP for RDP
    WINDOWS_RDP_PORT: int = 3389  # Default RDP port
    WINDOWS_RDP_PASSWORD: str = ""  # Password for dtx_user accounts

    # DICOM
    DICOM_WATCH_DIR: str = "/mnt/dicom-export"
    DICOM_ERROR_DIR: str = "/mnt/dicom-error"
    DICOM_PROCESSED_DIR: str = ""

    # Session limits
    SESSION_IDLE_TIMEOUT: int = 900   # 15 minutes
    SESSION_HARD_TIMEOUT: int = 3600  # 60 minutes
    SESSION_CHECK_INTERVAL: int = 60  # seconds between timeout checks
    MAX_CONCURRENT_SESSIONS: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
