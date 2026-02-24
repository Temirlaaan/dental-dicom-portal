# Dental DICOM Portal

Session management and orchestration layer for streaming DTX Studio via Apache Guacamole with automated DICOM ingestion.

Doctors access patient DICOM studies through browser-based RDP sessions to Windows VMs running DTX Studio, with centralized authentication, session lifecycle management, and full audit logging.

## Architecture

```
                          +------------------+
                          |    Frontend      |
                          | React + Vite     |
                          | :5173            |
                          +--------+---------+
                                   |
                    +--------------+--------------+
                    |                              |
            REST /api/*                   WebSocket /guacamole/*
                    |                              |
          +---------+---------+          +---------+---------+
          |   Backend API     |          |   Guacamole       |
          |   FastAPI         |          |   :8080           |
          |   :8000           |          +--------+----------+
          +---------+---------+                   |
                    |                         +---+---+
         +----------+----------+              | guacd |
         |          |          |              | :4822 |
    +----+---+ +----+---+ +---+------+       +---+---+
    |Keycloak| |  Postgres | | WinRM  |           |
    | :8180  | |  :5432  | | :5985  |     +------+------+
    +--------+ +---------+ +--------+     | Windows VM  |
                    |                     | RDP :3389   |
              +-----------+               | DTX Studio  |
              | 3 databases|              +-------------+
              | dental_portal
              | keycloak
              | guacamole_db
              +-----------+
```

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + TypeScript | React 19, TS 5.9 |
| Build Tool | Vite | 7.x |
| UI | Radix UI + Tailwind CSS | Tailwind 4.x |
| RDP Client | guacamole-common-js | 1.5.x |
| Data Fetching | TanStack React Query | 5.x |
| Backend | FastAPI (Python) | 0.109 |
| ORM | SQLAlchemy (async) | 2.0 |
| Database | PostgreSQL | 15 |
| Auth | Keycloak (OIDC) | 23.0 |
| RDP Proxy | Apache Guacamole | 1.5.4 |
| Session Host | Windows Server 2022 + RDS | - |
| WinRM | pywinrm (NTLM) | 0.4.3 |
| DICOM | pydicom + watchdog | 2.4.4 / 3.0 |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 1. Start infrastructure services
```bash
docker compose up -d
```

This starts PostgreSQL, Keycloak, Guacamole, and guacd.

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

The frontend uses `guacamole-common-js` for direct WebSocket tunnel connections to the Guacamole daemon, rendering the remote desktop on a `<canvas>` element instead of embedding Guacamole's webapp in an iframe.

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | React SPA |
| Backend API | http://localhost:8000 | FastAPI REST API |
| API Docs (Swagger) | http://localhost:8000/docs | Interactive API docs |
| Keycloak Admin | http://localhost:8180 | Identity management |
| Guacamole | http://localhost:8080/guacamole | RDP gateway admin |

## Default Credentials

| Service | Username | Password | Notes |
|---------|----------|----------|-------|
| PostgreSQL | postgres | postgres | Change in production |
| Keycloak Admin | admin | admin | Change in production |
| Guacamole | guacadmin | guacadmin | Change in production |

> **Note**: Keycloak realm users (doctors/admins) are configured in the `dental-portal` realm. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for auth setup details.

## Project Structure

```
epic-dental-dicom-portal/
+-- backend/
|   +-- app/
|   |   +-- core/           # Config, database, security
|   |   +-- middleware/      # Audit logging middleware
|   |   +-- models/          # SQLAlchemy ORM models (7 tables)
|   |   +-- routers/         # FastAPI route handlers (8 routers)
|   |   +-- schemas/         # Pydantic request/response schemas
|   |   +-- services/        # Business logic (sessions, DICOM, WinRM, Guacamole)
|   |   +-- main.py          # App entrypoint with lifespan tasks
|   +-- alembic/             # Database migrations
|   +-- requirements.txt
+-- frontend/
|   +-- src/
|   |   +-- components/      # UI components (GuacamoleDisplay, layouts, etc.)
|   |   +-- contexts/        # React contexts (Auth, Session)
|   |   +-- pages/           # Route pages (Login, Patients, Session, admin/*)
|   |   +-- services/        # API client hooks (React Query)
|   |   +-- types/           # TypeScript interfaces
|   |   +-- App.tsx           # Route definitions
|   +-- package.json
|   +-- vite.config.ts        # Dev proxy for /api and /guacamole
+-- scripts/
|   +-- init-databases.sql    # Creates 3 PostgreSQL databases
+-- docs/                     # Detailed documentation
+-- docker-compose.yml        # Infrastructure services
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design, VM pool model, session lifecycle, auth flow |
| [API Reference](docs/API.md) | All REST endpoints with request/response schemas |
| [Database Schema](docs/DATABASE.md) | All 7 tables, ER diagram, status enums |
| [Frontend](docs/FRONTEND.md) | Routes, components, contexts, GuacamoleDisplay |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Known issues, debug commands, state cleanup |

## Current Status

All 11 GitHub issues have been closed. The epic PR (#23) tracks the full feature branch (`epic/dental-dicom-portal`).

### Known Issues

See [Troubleshooting](docs/TROUBLESHOOTING.md) for details and workarounds:

- **White screen in RDP session** -- Resolved by switching from iframe embedding to `guacamole-common-js` WebSocket tunnel
- **RDP "wrong security type"** -- Requires `security: "nla"` in Guacamole connection params + Windows NLA registry settings
- **409 Conflict on session creation** -- Stuck sessions need manual DB cleanup or force-release via VM pool API
- **503 "No available VMs"** -- VMs stuck in `assigned` status can be force-released via `/api/vm-pool/{id}/force-release`
