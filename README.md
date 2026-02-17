# Dental DICOM Portal

Session management and orchestration layer for streaming DTX Studio via Apache Guacamole with automated DICOM ingestion.

## Architecture

- **Frontend**: React + TypeScript (Vite)
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Auth**: Keycloak (SSO, RBAC)
- **Session Streaming**: Apache Guacamole (RDP to browser)
- **Session Host**: Windows Server 2022 + RDS

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 1. Start infrastructure services
```bash
docker compose up -d
```

This starts PostgreSQL, Keycloak, and Guacamole.

### 2. Start backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Start frontend
```bash
cd frontend
npm install
npm run dev
```

### Service URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Keycloak Admin | http://localhost:8180 |
| Guacamole | http://localhost:8080/guacamole |

### Default Credentials
| Service | Username | Password |
|---------|----------|----------|
| PostgreSQL | postgres | postgres |
| Keycloak Admin | admin | admin |
| Guacamole | guacadmin | guacadmin |
