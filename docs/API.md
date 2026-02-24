# API Reference

**Base URL**: `http://localhost:8000` (dev) or `/api` (via Vite proxy)

**Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)

## Authentication

All endpoints except `/health` and `/api/auth/login` require a Bearer token:

```
Authorization: Bearer <access_token>
```

Access tokens are JWTs issued by Keycloak (RS256). Obtain one via the auth flow described below.

---

## Health

### `GET /health`

Health check endpoint. No authentication required.

**Response** `200`:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

## Auth

### `GET /api/auth/login`

Redirects to Keycloak login page. No authentication required.

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `redirect_uri` | string | `http://<host>:5173/auth/callback` | Where to redirect after login |

**Response** `302`: Redirect to Keycloak authorization endpoint.

---

### `GET /api/auth/callback`

Exchange an authorization code for tokens. No authentication required.

**Query Parameters**:
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | Yes | Authorization code from Keycloak |
| `redirect_uri` | string | No | Must match the redirect_uri used in login |

**Response** `200`:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 300,
  "scope": "openid profile email"
}
```

---

### `POST /api/auth/refresh`

Refresh an expired access token.

**Query Parameters**:
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | Yes | Refresh token from previous auth |

**Response** `200`: Same format as callback response.

---

### `GET /api/auth/me`

Get current authenticated user info.

**Auth**: Required (any role)

**Response** `200`:
```json
{
  "id": "keycloak-user-uuid",
  "username": "dr.smith",
  "email": "dr.smith@clinic.com",
  "name": "Dr. Smith",
  "roles": ["doctor"]
}
```

---

### `GET /api/auth/logout`

Redirects to Keycloak logout endpoint.

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `redirect_uri` | string | Frontend URL | Post-logout redirect |

**Response** `302`: Redirect to Keycloak logout.

---

## Patients

### `GET /api/patients`

List patients accessible to the current user. Doctors see only assigned patients; admins see all.

**Auth**: Required (any role)

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `search` | string | null | Filter by patient name (case-insensitive `ILIKE`) |
| `study_date_from` | date | null | Filter studies from this date |
| `study_date_to` | date | null | Filter studies to this date |
| `limit` | int (1-200) | 20 | Page size |
| `offset` | int | 0 | Page offset |

**Response** `200`:
```json
{
  "total": 42,
  "items": [
    {
      "id": "uuid",
      "patient_id": "DICOM-PAT-001",
      "name": "Smith, John",
      "created_at": "2026-02-20T10:00:00",
      "study_count": 3
    }
  ],
  "limit": 20,
  "offset": 0
}
```

---

### `GET /api/patients/{patient_id}`

Get patient details including studies.

**Auth**: Required (any role, access-controlled)

**Path Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `patient_id` | UUID | Patient UUID |

**Response** `200`:
```json
{
  "id": "uuid",
  "patient_id": "DICOM-PAT-001",
  "name": "Smith, John",
  "created_at": "2026-02-20T10:00:00",
  "study_count": 3,
  "studies": [
    {
      "id": "uuid",
      "study_instance_uid": "1.2.3.4.5",
      "study_date": "2026-01-15",
      "modality": "CT",
      "referring_physician": "Dr. Jones",
      "study_description": "Dental CT Scan",
      "series_description": "Axial",
      "created_at": "2026-02-20T10:00:00"
    }
  ]
}
```

**Error** `404`: Patient not found or not accessible.

---

### `GET /api/patients/{patient_id}/studies`

List studies for a specific patient.

**Auth**: Required (any role, access-controlled)

**Response** `200`: Array of `StudySchema` objects (same schema as in patient detail).

---

## Assignments

### `GET /api/assignments`

List patient-doctor assignments.

**Auth**: Required (admin only)

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `patient_id` | UUID | null | Filter by patient |
| `doctor_id` | UUID | null | Filter by doctor |

**Response** `200`:
```json
[
  {
    "id": "uuid",
    "patient_id": "uuid",
    "doctor_id": "uuid",
    "assigned_by": "uuid",
    "assigned_at": "2026-02-20T10:00:00"
  }
]
```

---

### `POST /api/assignments`

Create a patient-doctor assignment.

**Auth**: Required (admin only)

**Request Body**:
```json
{
  "patient_id": "uuid",
  "doctor_id": "uuid"
}
```

**Response** `201`: Created `AssignmentSchema` object.

**Errors**:
- `400`: Assignment already exists
- `404`: Patient or doctor not found

---

### `DELETE /api/assignments/{assignment_id}`

Delete a patient-doctor assignment.

**Auth**: Required (admin only)

**Response** `204`: No content.

**Error** `404`: Assignment not found.

---

## Doctors

### `GET /api/doctors`

List all registered doctors.

**Auth**: Required (admin only)

**Response** `200`:
```json
[
  {
    "id": "uuid",
    "keycloak_user_id": "keycloak-uuid",
    "name": "Dr. Smith",
    "email": "dr.smith@clinic.com",
    "created_at": "2026-02-20T10:00:00"
  }
]
```

---

## Audit Logs

### `GET /api/audit-logs`

List audit log entries with pagination and filtering.

**Auth**: Required (admin only)

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `user_id` | UUID | null | Filter by user |
| `action_type` | string | null | Filter by action (create/update/delete) |
| `resource_type` | string | null | Filter by resource (patients/sessions/etc.) |
| `date_from` | datetime | null | Filter from date |
| `date_to` | datetime | null | Filter to date |
| `limit` | int (1-500) | 50 | Page size |
| `offset` | int | 0 | Page offset |

**Response** `200`:
```json
{
  "total": 150,
  "items": [
    {
      "id": "uuid",
      "timestamp": "2026-02-20T10:00:00",
      "user_id": "uuid",
      "user_role": "admin",
      "action_type": "create",
      "resource_type": "sessions",
      "resource_id": "uuid",
      "details": {"status_code": 201, "path": "/api/sessions"},
      "ip_address": "10.0.0.1"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

---

### `GET /api/audit-logs/export`

Export audit logs as CSV file.

**Auth**: Required (admin only)

**Query Parameters**: Same filters as `GET /api/audit-logs` (without pagination).

**Response** `200`: CSV file download (`text/csv`).

CSV columns: `id, timestamp, user_id, user_role, action_type, resource_type, resource_id, ip_address, details`

---

## Sessions

### `POST /api/sessions`

Create a new RDP session. Provisions a VM, mounts SMB, creates Guacamole connection, launches DTX Studio.

**Auth**: Required (doctor only)

**Request Body**:
```json
{
  "patient_id": "uuid"
}
```

**Response** `201`:
```json
{
  "id": "uuid",
  "doctor_id": "uuid",
  "patient_id": "uuid",
  "study_id": null,
  "guacamole_connection_id": "42",
  "rds_session_id": null,
  "vm_instance_id": "uuid",
  "vm_ip": "10.121.245.200",
  "windows_user": "Administrator",
  "status": "active",
  "started_at": "2026-02-20T10:00:00",
  "last_activity_at": "2026-02-20T10:00:00",
  "ended_at": null
}
```

**Errors**:
- `404`: Doctor profile not found
- `409`: Doctor already has an active session
- `429`: Global concurrent session limit reached
- `500`: Session creation failed (VM/WinRM/Guacamole error)
- `503`: No available VMs in the pool

---

### `GET /api/sessions`

List sessions. Admins see all; doctors see only their own.

**Auth**: Required (any role)

**Response** `200`: Array of `SessionSchema` objects.

---

### `GET /api/sessions/{session_id}`

Get a single session by ID.

**Auth**: Required (any role, access-controlled)

**Response** `200`: `SessionSchema` object.

**Errors**:
- `403`: Not authorized to view this session
- `404`: Session not found

---

### `DELETE /api/sessions/{session_id}`

Terminate a session. Cleans up Guacamole connection, WinRM session, and releases VM.

**Auth**: Required (owner doctor or admin)

**Response** `204`: No content.

**Errors**:
- `400`: Session already terminated
- `403`: Not authorized to terminate this session
- `404`: Session not found

---

### `POST /api/sessions/{session_id}/extend`

Extend a session by updating the last activity timestamp. Resets `idle_warning` status back to `active`.

**Auth**: Required (owner doctor or admin)

**Response** `200`: Updated `SessionSchema` object.

**Errors**:
- `400`: Session not in extendable state
- `403`: Not authorized to extend this session
- `404`: Session not found

---

### `GET /api/sessions/{session_id}/guacamole-url`

Get Guacamole connection parameters for the frontend WebSocket tunnel.

**Auth**: Required (owner doctor or admin)

**Response** `200`:
```json
{
  "url": "/guacamole/#/client/<base64>?token=<token>",
  "token": "<guacamole_auth_token>",
  "connection_id": "42",
  "datasource": "postgresql"
}
```

**Errors**:
- `400`: No Guacamole connection on this session, or session not active
- `403`: Not authorized to access this session
- `404`: Session not found

---

## VM Pool

All VM pool endpoints require **admin** role.

### `GET /api/vm-pool`

List all VMs in the pool.

**Response** `200`:
```json
[
  {
    "id": "uuid",
    "hostname": "WIN-VM-01",
    "ip_address": "10.121.245.200",
    "rdp_port": 3389,
    "winrm_port": 5985,
    "status": "ready",
    "doctor_id": null,
    "doctor_name": null,
    "session_id": null,
    "mounted_share": null,
    "assigned_at": null,
    "last_health_check": "2026-02-20T10:00:00",
    "created_at": "2026-02-19T08:00:00"
  }
]
```

---

### `POST /api/vm-pool`

Register a new VM in the pool.

**Request Body**:
```json
{
  "hostname": "WIN-VM-02",
  "ip_address": "10.121.245.201",
  "rdp_port": 3389,
  "winrm_port": 5985
}
```

**Response** `201`: Created `VMResponse` object.

---

### `DELETE /api/vm-pool/{vm_id}`

Delete a VM from the pool (only if not currently assigned).

**Response** `204`: No content.

**Errors**:
- `404`: VM not found
- `409`: Cannot delete while assigned to a session

---

### `POST /api/vm-pool/{vm_id}/health-check`

Check VM health via WinRM. Updates `last_health_check` timestamp and transitions status between `ready`/`offline`.

**Response** `200`: Updated `VMResponse` object.

---

### `POST /api/vm-pool/{vm_id}/force-release`

Force-release a stuck VM back to the pool. Attempts WinRM cleanup (best-effort), then resets all assignment fields.

**Response** `200`: Updated `VMResponse` (status will be `ready`).

**Error** `400`: VM is not in `assigned` status.

---

## Error Response Format

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request / Invalid state |
| 401 | Invalid or expired token |
| 403 | Insufficient role or not authorized for this resource |
| 404 | Resource not found |
| 409 | Conflict (duplicate assignment, VM in use) |
| 429 | Session limit reached |
| 500 | Internal server error |
| 503 | No available VMs |

---

## Pydantic Schemas Reference

| Schema | File | Used By |
|--------|------|---------|
| `HealthResponse` | `schemas/health.py` | `GET /health` |
| `PatientSchema` | `schemas/patient.py` | Patient list items |
| `PatientDetail` | `schemas/patient.py` | Single patient with studies |
| `PaginatedPatientList` | `schemas/patient.py` | Patient list response |
| `StudySchema` | `schemas/study.py` | Study details |
| `AssignmentCreate` | `schemas/assignment.py` | `POST /api/assignments` request |
| `AssignmentSchema` | `schemas/assignment.py` | Assignment responses |
| `AuditLogSchema` | `schemas/audit_log.py` | Audit log entries |
| `PaginatedAuditLogList` | `schemas/audit_log.py` | Audit log list response |
| `SessionCreate` | `schemas/session.py` | `POST /api/sessions` request |
| `SessionSchema` | `schemas/session.py` | Session responses |
| `DoctorSchema` | `routers/doctors.py` | Doctor list (inline schema) |
| `VMCreateRequest` | `routers/vm_pool.py` | `POST /api/vm-pool` request |
| `VMResponse` | `routers/vm_pool.py` | VM pool responses |
