# Architecture

## System Overview

The Dental DICOM Portal provides browser-based access to DTX Studio running on Windows VMs. The system orchestrates RDP sessions through Apache Guacamole, manages DICOM data ingestion, and enforces role-based access control via Keycloak.

```
+------------------+        +------------------+        +------------------+
|                  |  OIDC  |                  |  REST  |                  |
|     Browser      +------->+    Keycloak      |<-------+   Backend API    |
|  (React SPA)     |        |   (IdP)          |  JWKS  |   (FastAPI)      |
|                  |        +------------------+        +--------+---------+
+-------+----------+                                             |
        |                                              +---------+---------+
        | WebSocket                                    |         |         |
        | (guacamole-common-js)                   +----+--+ +----+--+ +---+-----+
        |                                         |Postgres| |WinRM  | |Guacamole|
+-------v----------+                              | (ORM)  | |Client | |REST API |
|   Guacamole      |                              +--------+ +---+---+ +----+----+
|   Webapp :8080   |                                              |          |
+-------+----------+                                              |          |
        |                                                   +-----v----------v--+
+-------v----------+                                        |    Windows VM     |
|     guacd        |   RDP                                  |  - DTX Studio     |
|   (RDP proxy)    +--------------------------------------->+  - SMB share      |
|     :4822        |                                        |  - RDP :3389      |
+------------------+                                        |  - WinRM :5985    |
                                                            +-------------------+
```

## Components

### Backend API (FastAPI)

**Location**: `backend/app/`

The Python backend handles all business logic:

- **Authentication**: Validates Keycloak JWT tokens (RS256) using JWKS endpoint
- **Session orchestration**: Creates/terminates RDP sessions, manages VM pool
- **DICOM ingestion**: Watches filesystem for `.dcm` files, parses with pydicom, stores in DB
- **Audit logging**: Middleware logs all mutating API requests (POST/PUT/PATCH/DELETE)
- **Background tasks**: Session timeout monitor and orphaned session cleanup

Entry point: `backend/app/main.py`

### Frontend (React + TypeScript)

**Location**: `frontend/src/`

Single-page application with two layout modes:

- **Doctor view**: Patient list, session launch, RDP viewer (GuacamoleDisplay)
- **Admin view**: Session management, patient-doctor assignments, audit logs, system health

The RDP viewer uses `guacamole-common-js` to create a WebSocket tunnel directly to guacd, rendering the remote desktop on an HTML5 `<canvas>`. See [FRONTEND.md](FRONTEND.md) for details.

### Keycloak (Identity Provider)

**Port**: 8180

Provides OpenID Connect (OIDC) authentication:

- **Realm**: `dental-portal`
- **Clients**: `dental-frontend` (public, PKCE), `dental-backend` (confidential)
- **Roles**: `admin`, `doctor` (realm roles)
- **Flow**: Authorization Code with PKCE -> JWT access tokens (RS256)

### Apache Guacamole

**Ports**: 8080 (webapp), 4822 (guacd daemon)

Clientless remote desktop gateway:

- **guacamole**: Java webapp that manages connections via REST API and PostgreSQL
- **guacd**: Native daemon that translates between Guacamole protocol and RDP/VNC/SSH
- **Datasource**: `postgresql` (connection definitions stored in `guacamole_db`)

The backend creates/deletes RDP connections via Guacamole's REST API. The frontend connects via WebSocket tunnel (`/guacamole/websocket-tunnel`) using `guacamole-common-js`, bypassing the Guacamole webapp UI entirely.

### PostgreSQL

**Port**: 5432

Three databases on a single PostgreSQL 15 instance:

| Database | Purpose |
|----------|---------|
| `dental_portal` | Application data (patients, studies, sessions, VMs, audit logs) |
| `keycloak` | Keycloak identity data |
| `guacamole_db` | Guacamole connection definitions and user permissions |

### Windows VM (Session Host)

Each VM runs:
- **Windows Server 2022** with Remote Desktop Services
- **DTX Studio** dental imaging software
- **WinRM** (port 5985) for remote PowerShell/cmd execution
- **RDP** (port 3389) for graphical session access via Guacamole

---

## VM Pool Model

The system uses a **1 VM = 1 doctor** model. Each VM in the pool is either free or exclusively assigned to one doctor's session.

### VM Status State Machine

```
                 register
    +--------+  (API POST)
    |  ready |<-----------+
    +---+----+            |
        |                 |
  assign to session  force-release /
        |            session end
        v                 |
    +--------+            |
    |assigned+------------+
    +---+----+
        |
  health check fails
        |
        v
    +---------+
    | offline |
    +---------+
        |
  health check passes
        |
        v
    +--------+
    |  ready |
    +--------+
```

| Status | Description |
|--------|-------------|
| `ready` | Available for assignment to a new session |
| `assigned` | Bound to a doctor/session -- SMB mounted, DTX running, RDP active |
| `offline` | Health check failed -- excluded from assignment until recovered |

### VM Assignment Fields

When a VM is assigned, the `vm_instances` row is updated with:
- `doctor_id` -- UUID of the assigned doctor
- `doctor_name` -- Display name (denormalized for admin UI)
- `session_id` -- UUID of the active session
- `mounted_share` -- Drive letter of the mounted SMB share (e.g., `Z:`)
- `assigned_at` -- Timestamp of assignment

When released, all these fields are set to `NULL` and status returns to `ready`.

---

## Session Lifecycle

### Session Status State Machine

```
  POST /api/sessions
        |
        v
   +----------+
   | creating |  (VM assigned, SMB mounting, Guacamole connection creating)
   +----+-----+
        |
   success
        |
        v
   +--------+
   | active |  (RDP connected, DTX Studio running)
   +---+----+
       |
  idle timeout (15 min)
       |
       v
  +------------+
  |idle_warning|  (frontend shows warning dialog)
  +-----+------+
        |
   extend (user clicks "Extend")
        |----> back to active
        |
   hard timeout (60 min) / user ends / admin terminates
        |
        v
  +----------+
  |terminated|  (Guacamole deleted, VM cleaned, SMB unmounted)
  +----------+
```

### Session Creation Steps

1. **Concurrency check**: Verify doctor has no active session; check global limit (`MAX_CONCURRENT_SESSIONS`)
2. **VM allocation**: Find a VM with `status=ready`, mark it `assigned`
3. **SMB mount**: Via WinRM, mount doctor's DICOM share on the VM (`Z:` drive)
4. **Guacamole connection**: Create RDP connection via Guacamole REST API (NLA security, cert ignore)
5. **DTX Studio launch**: Via WinRM, start DTX Studio with DICOM path argument
6. **Status update**: Session moves from `creating` to `active`

On failure at any step, the system rolls back: cleans up Guacamole connection, WinRM session, and releases the VM back to the pool.

### Session Termination Steps

1. **Guacamole cleanup**: Delete the RDP connection via REST API
2. **VM cleanup**: Kill DTX Studio processes, unmount SMB share via WinRM
3. **VM release**: Reset VM status to `ready`, clear assignment fields
4. **Session update**: Set `status=terminated`, `ended_at=now()`

---

## Authentication Flow

```
Browser                    Backend                  Keycloak
  |                           |                        |
  |-- GET /api/auth/login --->|                        |
  |<-- 302 Redirect ----------|                        |
  |                           |                        |
  |-- Authorization Code ----------------------------->|
  |<-- Code + redirect -------------------------------|
  |                           |                        |
  |-- GET /api/auth/callback?code=xxx -->|             |
  |                           |-- POST /token -------->|
  |                           |<-- JWT tokens ---------|
  |<-- {access_token, refresh_token} ----|             |
  |                           |                        |
  |-- API requests with       |                        |
  |   Authorization: Bearer   |                        |
  |   <access_token>          |                        |
  |                           |-- Fetch JWKS --------->|
  |                           |<-- Public keys --------|
  |                           |-- Verify RS256 JWT     |
  |                           |-- Extract realm roles  |
  |                           |   (admin/doctor)       |
```

- **Token format**: JWT signed with RS256 by Keycloak
- **Token validation**: Backend fetches JWKS from `{KEYCLOAK_URL}/realms/{realm}/protocol/openid-connect/certs`, caches keys, verifies signature
- **Role extraction**: From `realm_access.roles` claim in the JWT payload
- **Token refresh**: Frontend auto-refreshes every 4 minutes via `POST /api/auth/refresh`
- **Token storage**: `sessionStorage` (primary) + `localStorage` (for API interceptor)

---

## DICOM Ingestion Pipeline

```
/mnt/dicom-export/        DicomWatcher         DicomParser        DicomIngestion
  (filesystem)            (watchdog)           (pydicom)          (SQLAlchemy)
      |                       |                    |                    |
  .dcm file created           |                    |                    |
      +-----> on_created ---->|                    |                    |
              (debounce 0.2s) |                    |                    |
                              +-- extract_tags --->|                    |
                              |                    |-- dcmread() ------>|
                              |                    |<- DicomData -------|
                              |                    |                    |
                              +-- ingest_dicom --------------------------->|
                              |                    |                    |-- get/create Patient
                              |                    |                    |-- create Study
                              |                    |                    |-- commit
                              |                    |                    |
                              +-- move_to_processed/error               |
```

The DICOM watcher is a separate process (`backend/app/services/__main__.py`) that:

1. Uses `watchdog` to monitor `DICOM_WATCH_DIR` for new `.dcm` files
2. Deduplicates events (2-second window, max 500 tracked paths)
3. Extracts DICOM tags with `pydicom` (PatientID, StudyInstanceUID, Modality, etc.)
4. Converts patient names from `LAST^FIRST` to `Last, First` format
5. Creates Patient record if not exists (handles race conditions)
6. Creates Study record (skips duplicates via unique `study_instance_uid`)
7. Moves processed files to `DICOM_PROCESSED_DIR` or errors to `DICOM_ERROR_DIR`

---

## Guacamole Integration

### Connection Management

The backend manages Guacamole connections via its REST API (`GuacamoleClient` in `backend/app/services/guacamole_client.py`):

1. **Authentication**: `POST /api/tokens` with admin credentials -> `authToken`
2. **Create connection**: `POST /api/session/data/postgresql/connections` with RDP parameters
3. **Delete connection**: `DELETE /api/session/data/postgresql/connections/{id}`
4. **Generate client token**: Currently returns admin token (demo mode)

### RDP Connection Parameters

```json
{
  "protocol": "rdp",
  "parameters": {
    "hostname": "<vm_ip>",
    "port": "3389",
    "username": "<rdp_user>",
    "password": "<rdp_password>",
    "security": "nla",
    "ignore-cert": "true",
    "enable-wallpaper": "false",
    "enable-theming": "false",
    "enable-font-smoothing": "false",
    "enable-full-window-drag": "false",
    "enable-desktop-composition": "false",
    "enable-menu-animations": "false"
  }
}
```

### Frontend WebSocket Tunnel

The `GuacamoleDisplay` component (`frontend/src/components/GuacamoleDisplay.tsx`) connects via:

1. Creates `Guacamole.WebSocketTunnel` to `/guacamole/websocket-tunnel` (proxied by Vite to `:8080`)
2. Creates `Guacamole.Client` with the tunnel
3. Connects with params: `token`, `GUAC_ID`, `GUAC_TYPE=c`, `GUAC_DATA_SOURCE=postgresql`, `GUAC_WIDTH`, `GUAC_HEIGHT`, `GUAC_DPI`
4. Renders remote desktop on `<canvas>`, handles keyboard/mouse forwarding
5. Auto-scales display to fit container

---

## WinRM Orchestration

The `WinRMClient` (`backend/app/services/winrm_client.py`) manages Windows VMs via WinRM (NTLM auth, port 5985):

| Operation | Method | Description |
|-----------|--------|-------------|
| Mount SMB | `mount_smb_share()` | `net use Z: \\server\share /user:svc_xxx password` |
| Unmount SMB | `unmount_smb_share()` | `net use Z: /delete /y` |
| Launch DTX | `launch_dtx_studio()` | `Start-Process DTXStudio.exe -ArgumentList "<dicom_path>"` |
| Health check | `check_vm_health()` | `Write-Output "OK"` via PowerShell |
| Cleanup | `cleanup_vm_session()` | Kill DTX processes + unmount SMB |

The client uses a Protocol-based abstraction with `MockWinRMClient` for testing without Windows infrastructure. When `WINRM_HOST` is empty, the mock client is used.

---

## Background Tasks

Two `asyncio` tasks run during the FastAPI lifespan (started in `backend/app/main.py`):

### Session Timeout Monitor

**Interval**: `SESSION_CHECK_INTERVAL` (default 60 seconds)

- Queries all sessions with `status IN ('active', 'idle_warning')` and `ended_at IS NULL`
- **Hard timeout** (`SESSION_HARD_TIMEOUT`, default 3600s): Terminates session, cleans up Guacamole/WinRM resources, releases VM
- **Idle timeout** (`SESSION_IDLE_TIMEOUT`, default 900s): Sets session status to `idle_warning`
- Logs audit entries for `session_terminated` and `session_idle_warning`

### Orphaned Session Cleanup

**Interval**: 3600 seconds (1 hour)

- Finds sessions that are still `active`/`idle_warning` but started more than `2 * SESSION_HARD_TIMEOUT` seconds ago
- Terminates them and cleans up all resources
- Logs audit entries for `session_orphan_cleanup`

---

## Audit Logging

The `AuditMiddleware` (`backend/app/middleware/audit.py`) automatically logs:

- **Trigger**: All successful POST, PUT, PATCH, DELETE requests
- **Extraction**: User ID and role from JWT (unverified claims for performance), client IP from `X-Forwarded-For` or connection
- **Storage**: `audit_logs` table with action type, resource type/ID, details (status code, path)
- **Action mapping**: POST -> `create`, PUT/PATCH -> `update`, DELETE -> `delete`

Background tasks also log audit entries directly for automated actions (session termination, orphan cleanup).

---

## Network Topology (Development)

| Service | Host | Port |
|---------|------|------|
| Frontend (Vite dev) | localhost | 5173 |
| Backend API | localhost | 8000 |
| PostgreSQL | localhost | 5432 |
| Keycloak | localhost (10.121.245.146) | 8180 |
| Guacamole webapp | localhost | 8080 |
| guacd | guacd (Docker) | 4822 |
| Windows VM (WinRM) | VM IP | 5985 |
| Windows VM (RDP) | VM IP | 3389 |

The Vite dev server proxies `/api/*` to the backend (`:8000`) and `/guacamole/*` to Guacamole (`:8080`), including WebSocket upgrades for the tunnel.
