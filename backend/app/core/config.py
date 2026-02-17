from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dental_portal"

    # Keycloak
    KEYCLOAK_URL: str = "http://localhost:8180"
    KEYCLOAK_REALM: str = "dental-portal"
    KEYCLOAK_CLIENT_ID: str = "dental-portal-backend"
    KEYCLOAK_CLIENT_SECRET: str = ""

    # Guacamole
    GUACAMOLE_URL: str = "http://localhost:8080/guacamole"

    # Windows Server (WinRM)
    WINRM_HOST: str = ""
    WINRM_USER: str = ""
    WINRM_PASSWORD: str = ""

    # DICOM
    DICOM_WATCH_DIR: str = "/mnt/dicom-export"

    # Session limits
    SESSION_IDLE_TIMEOUT: int = 900  # 15 minutes
    SESSION_HARD_TIMEOUT: int = 3600  # 60 minutes
    MAX_CONCURRENT_SESSIONS: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
