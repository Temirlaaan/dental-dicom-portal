# Database Schema

**Engine**: PostgreSQL 15
**ORM**: SQLAlchemy 2.0 (async via asyncpg)
**Migrations**: Alembic

The application database (`dental_portal`) contains 7 tables. Two other databases (`keycloak`, `guacamole_db`) are managed by their respective services.

## Entity Relationship Diagram

```
+------------------+       +---------------------+       +------------------+
|    patients      |       | patient_assignments  |       |     doctors      |
+------------------+       +---------------------+       +------------------+
| id          (PK) |<------| patient_id (FK)      |------>| id          (PK) |
| patient_id  (UQ) |       | doctor_id  (FK)      |       | keycloak_user_id |
| name             |       | id            (PK)   |       | name             |
| created_at       |       | assigned_by          |       | email       (UQ) |
+--------+---------+       | assigned_at          |       | created_at       |
         |                  +---------------------+       +------------------+
         |
         | 1:N
         |
+--------v---------+
|     studies       |
+------------------+
| id          (PK) |
| patient_id  (FK) |
| study_instance_uid (UQ)
| study_date       |
| modality         |
| referring_physician
| study_description|
| series_description
| file_path        |
| created_at       |
+------------------+


+------------------+       +------------------+
|    sessions      |       |  vm_instances    |
+------------------+       +------------------+
| id          (PK) |       | id          (PK) |
| doctor_id   (FK) |       | hostname    (UQ) |
| patient_id  (FK) |       | ip_address  (UQ) |
| study_id    (FK) |       | rdp_port         |
| guacamole_      |       | winrm_port       |
|  connection_id   |       | status      (IX) |
| rds_session_id   |       | doctor_id        |
| vm_instance_id   |------>| doctor_name      |
| vm_ip            |       | session_id       |
| windows_user     |       | mounted_share    |
| status      (IX) |       | assigned_at      |
| started_at       |       | last_health_check|
| last_activity_at |       | created_at       |
| ended_at         |       +------------------+
+------------------+


+------------------+
|   audit_logs     |
+------------------+
| id          (PK) |
| timestamp   (IX) |
| user_id          |
| user_role        |
| action_type (IX) |
| resource_type    |
| resource_id      |
| details    (JSONB)|
| ip_address       |
+------------------+

Legend: PK=Primary Key, FK=Foreign Key, UQ=Unique, IX=Indexed
```

---

## Tables

### `patients`

Patients identified by DICOM PatientID. Created automatically during DICOM ingestion.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | Internal identifier |
| `patient_id` | VARCHAR | UNIQUE, INDEX | DICOM PatientID tag |
| `name` | VARCHAR | NOT NULL | Patient name (formatted as "Last, First") |
| `created_at` | TIMESTAMP | default `now()` | Record creation time |

**Relationships**:
- `studies` -- one-to-many with `studies.patient_id`
- `assignments` -- one-to-many with `patient_assignments.patient_id`

**Source**: `backend/app/models/patient.py`

---

### `studies`

DICOM studies extracted from `.dcm` files by the ingestion pipeline.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | Internal identifier |
| `patient_id` | UUID | FK -> `patients.id` | Owning patient |
| `study_instance_uid` | VARCHAR | UNIQUE, INDEX | DICOM StudyInstanceUID |
| `study_date` | DATE | NOT NULL | DICOM StudyDate |
| `modality` | VARCHAR | NOT NULL | DICOM Modality (CT, OT, etc.) |
| `referring_physician` | VARCHAR | NULLABLE | DICOM ReferringPhysicianName |
| `study_description` | VARCHAR | NULLABLE | DICOM StudyDescription |
| `series_description` | VARCHAR | NULLABLE | DICOM SeriesDescription |
| `file_path` | VARCHAR | NOT NULL | Path to the original `.dcm` file |
| `created_at` | TIMESTAMP | default `now()` | Record creation time |

**Relationships**:
- `patient` -- many-to-one with `patients.id`

**Source**: `backend/app/models/study.py`

---

### `doctors`

Doctors linked to Keycloak user accounts. Must be registered before they can receive patient assignments or create sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | Internal identifier |
| `keycloak_user_id` | VARCHAR | UNIQUE, INDEX | Keycloak `sub` claim |
| `name` | VARCHAR | NOT NULL | Display name |
| `email` | VARCHAR | UNIQUE | Email address |
| `created_at` | TIMESTAMP | default `now()` | Record creation time |

**Relationships**:
- `assignments` -- one-to-many with `patient_assignments.doctor_id`

**Source**: `backend/app/models/doctor.py`

---

### `patient_assignments`

Links patients to doctors. Controls which patients a doctor can see and create sessions for.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | Internal identifier |
| `patient_id` | UUID | FK -> `patients.id` | Assigned patient |
| `doctor_id` | UUID | FK -> `doctors.id` | Assigned doctor |
| `assigned_by` | UUID | NULLABLE | Admin user ID who made the assignment |
| `assigned_at` | TIMESTAMP | default `now()` | Assignment time |

**Relationships**:
- `patient` -- many-to-one with `patients.id`
- `doctor` -- many-to-one with `doctors.id`

**Source**: `backend/app/models/assignment.py`

---

### `sessions`

RDP session records tracking the full lifecycle from creation to termination.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | Internal identifier |
| `doctor_id` | UUID | FK -> `doctors.id` | Session owner |
| `patient_id` | UUID | FK -> `patients.id` | Patient being viewed |
| `study_id` | UUID | FK -> `studies.id`, NULLABLE | Specific study (optional) |
| `guacamole_connection_id` | VARCHAR | NULLABLE | Guacamole connection identifier |
| `rds_session_id` | VARCHAR | NULLABLE | Windows RDS session ID |
| `vm_instance_id` | UUID | NULLABLE | Assigned VM from pool |
| `vm_ip` | VARCHAR | NULLABLE | VM IP address (denormalized) |
| `windows_user` | VARCHAR | NULLABLE | Windows username used for RDP |
| `status` | VARCHAR | INDEX, default `creating` | Session lifecycle status |
| `started_at` | TIMESTAMP | default `now()` | Session start time |
| `last_activity_at` | TIMESTAMP | NULLABLE | Last user activity (for idle timeout) |
| `ended_at` | TIMESTAMP | NULLABLE | Session end time |

**Source**: `backend/app/models/session.py`

---

### `vm_instances`

Pool of Windows VMs available for RDP sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | Internal identifier |
| `hostname` | VARCHAR | UNIQUE, NOT NULL | VM hostname (e.g., `WIN-VM-01`) |
| `ip_address` | VARCHAR | UNIQUE, NOT NULL | VM IP address |
| `rdp_port` | INTEGER | default 3389 | RDP port |
| `winrm_port` | INTEGER | default 5985 | WinRM port |
| `status` | VARCHAR | INDEX, default `ready` | VM pool status |
| `doctor_id` | UUID | NULLABLE | Currently assigned doctor |
| `doctor_name` | VARCHAR | NULLABLE | Doctor display name (denormalized) |
| `session_id` | UUID | NULLABLE | Currently assigned session |
| `mounted_share` | VARCHAR | NULLABLE | Mounted drive letter (e.g., `Z:`) |
| `assigned_at` | TIMESTAMP | NULLABLE | Assignment time |
| `last_health_check` | TIMESTAMP | NULLABLE | Last health check time |
| `created_at` | TIMESTAMP | default `now()` | Registration time |

**Source**: `backend/app/models/vm_instance.py`

---

### `audit_logs`

Immutable audit trail of all mutating API operations and system events.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default `uuid4()` | Internal identifier |
| `timestamp` | TIMESTAMP | INDEX, default `now()` | Event time |
| `user_id` | UUID | NULLABLE | Acting user (null for system events) |
| `user_role` | VARCHAR | NULLABLE | User's first role at time of action |
| `action_type` | VARCHAR | INDEX | `create`, `update`, `delete`, `session_terminated`, etc. |
| `resource_type` | VARCHAR | NOT NULL | Resource category (patients, sessions, etc.) |
| `resource_id` | VARCHAR | NULLABLE | Specific resource identifier |
| `details` | JSONB | NULLABLE | Additional context (status_code, path, source) |
| `ip_address` | VARCHAR | NULLABLE | Client IP address |

**Source**: `backend/app/models/audit.py`

---

## Status Enums

### VM Statuses (`vm_instances.status`)

| Value | Description |
|-------|-------------|
| `ready` | Available for assignment |
| `assigned` | Bound to an active session |
| `offline` | Health check failed |

### Session Statuses (`sessions.status`)

| Value | Description |
|-------|-------------|
| `creating` | VM assigned, resources being provisioned |
| `active` | Fully operational, user connected |
| `idle_warning` | User idle for > 15 minutes, warning shown |
| `terminated` | Session ended, resources cleaned up |

---

## Migration History

| Revision | Description | File |
|----------|-------------|------|
| `003_vm_pool` | Add `vm_instances` table and `vm_instance_id`/`vm_ip` columns to `sessions` | `alembic/versions/003_vm_pool.py` |

> **Note**: The initial tables (patients, studies, doctors, patient_assignments, sessions, audit_logs) were created outside of Alembic tracking. The `003_vm_pool` migration has `down_revision = None` (no parent).

---

## Database Initialization

The `scripts/init-databases.sql` file runs on first PostgreSQL startup and creates the three databases:

```sql
CREATE DATABASE dental_portal;
CREATE DATABASE keycloak;
CREATE DATABASE guacamole_db;
```

Guacamole's schema is auto-initialized by the Guacamole Docker image. The application schema is managed via Alembic (`alembic upgrade head`). Keycloak manages its own schema.
