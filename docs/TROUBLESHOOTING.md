# Troubleshooting

## Known Issues and Solutions

### 1. White Screen in RDP Session (iframe approach)

**Problem**: Embedding Guacamole's Angular webapp via `<iframe>` resulted in a white screen because:
- The Guacamole SPA uses hash-fragment routing (`#/client/...`) which conflicts with token parameters
- Cookie/session isolation between iframe and parent page
- Cross-origin restrictions with the Guacamole webapp

**Solution**: The project now uses `guacamole-common-js` to connect directly via WebSocket tunnel, rendering on a `<canvas>` element. This bypasses the Guacamole webapp entirely.

**Relevant files**:
- `frontend/src/components/GuacamoleDisplay.tsx` -- WebSocket tunnel + canvas rendering
- `frontend/src/services/doctorApi.ts` -- `useGuacamoleUrl()` hook
- `backend/app/routers/sessions.py:180` -- `get_guacamole_url` endpoint

If you still see a white screen with the current implementation, check:
1. Vite proxy is correctly configured for `/guacamole` with `ws: true`
2. Guacamole container is running: `docker compose ps guacamole`
3. guacd container is running: `docker compose ps guacd`
4. The WebSocket tunnel URL resolves correctly (see debugging section below)

---

### 2. RDP "Wrong Security Type" Error

**Problem**: Guacamole fails to connect with "The server's security type is not supported" or similar RDP negotiation errors.

**Solution**: The Guacamole connection must use `"security": "nla"` (Network Level Authentication). This is already set in `backend/app/services/guacamole_client.py:89`.

If the error persists, check the **Windows VM configuration**:

1. Enable NLA on the Windows VM:
   ```powershell
   # Run on the Windows VM
   Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name 'SecurityLayer' -Value 2
   Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name 'UserAuthentication' -Value 1
   ```

2. Ensure the RDP user account has a password set (NLA requires credentials).

3. If using `ignore-cert: true`, the server certificate is not validated. This is fine for development but should be replaced with proper certificates in production.

---

### 3. 409 Conflict: "Doctor already has an active session"

**Problem**: Creating a new session fails with HTTP 409 because the doctor already has a session in `creating`, `active`, or `idle_warning` status.

**Cause**: A previous session was not properly terminated (e.g., browser closed without ending session, backend error during cleanup).

**Solutions**:

**Option A -- Terminate via API** (preferred):
```bash
# List sessions to find the stuck one
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/sessions | python3 -m json.tool

# Terminate the stuck session
curl -X DELETE -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/sessions/<session_id>
```

**Option B -- Direct database cleanup**:
```sql
-- Find stuck sessions for the doctor
SELECT id, status, started_at, ended_at
FROM sessions
WHERE doctor_id = '<doctor_uuid>'
  AND status IN ('creating', 'active', 'idle_warning')
  AND ended_at IS NULL;

-- Force-terminate the stuck session
UPDATE sessions
SET status = 'terminated', ended_at = NOW()
WHERE id = '<session_id>';
```

Then release the VM (see issue #4 below).

---

### 4. 503 "No Available VMs in the Pool"

**Problem**: Session creation fails because all VMs are in `assigned` status.

**Cause**: VMs were not released back to the pool after session termination (due to errors during cleanup).

**Solutions**:

**Option A -- Force-release via API** (admin only):
```bash
# List VMs to find stuck ones
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/vm-pool | python3 -m json.tool

# Force-release a stuck VM
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/vm-pool/<vm_id>/force-release
```

**Option B -- Direct database cleanup**:
```sql
-- Find stuck VMs
SELECT id, hostname, ip_address, status, doctor_id, session_id
FROM vm_instances
WHERE status = 'assigned';

-- Release back to pool
UPDATE vm_instances
SET status = 'ready',
    doctor_id = NULL,
    doctor_name = NULL,
    session_id = NULL,
    mounted_share = NULL,
    assigned_at = NULL
WHERE id = '<vm_id>';
```

**Prevention**: The orphaned session cleanup background task runs every hour and should catch these cases automatically. Check backend logs for errors.

---

### 5. Guacamole Connection Fails After Token Expires

**Problem**: The Guacamole auth token (returned by `get_guacamole_url`) expires after the Guacamole session timeout.

**Current workaround**: The `useGuacamoleUrl` hook uses `staleTime: Infinity` so it doesn't refetch. If the connection drops, the user needs to end and restart the session.

**Future fix**: Implement proper token refresh in the GuacamoleDisplay component or use Guacamole's authentication extension for Keycloak integration.

---

### 6. Windows VM Activation

**Problem**: Windows Server evaluation license expires.

**Workaround**: Re-arm the evaluation period:
```powershell
slmgr /rearm
Restart-Computer
```

This can be done up to 3 times for 180-day evaluation licenses.

---

## Debugging Commands

### Check Service Health

```bash
# All Docker services
docker compose ps

# Backend health
curl http://localhost:8000/health

# Keycloak (check realm exists)
curl http://localhost:8180/realms/dental-portal

# Guacamole API (get auth token)
curl -X POST http://localhost:8080/guacamole/api/tokens \
  -d "username=guacadmin&password=guacadmin"
```

### Check Guacamole WebSocket Tunnel

```bash
# Test the tunnel endpoint (should return 400 since it expects WebSocket upgrade)
curl -v http://localhost:8080/guacamole/websocket-tunnel

# Test through Vite proxy (if frontend is running)
curl -v http://localhost:5173/guacamole/websocket-tunnel

# List Guacamole connections via API
TOKEN=$(curl -s -X POST http://localhost:8080/guacamole/api/tokens \
  -d "username=guacadmin&password=guacadmin" | python3 -c "import sys,json; print(json.load(sys.stdin)['authToken'])")

curl -s "http://localhost:8080/guacamole/api/session/data/postgresql/connections?token=$TOKEN" | python3 -m json.tool
```

### Database Queries

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d dental_portal
```

```sql
-- Active sessions
SELECT s.id, s.status, s.vm_ip, s.started_at, d.name as doctor
FROM sessions s
JOIN doctors d ON d.id = s.doctor_id
WHERE s.ended_at IS NULL
ORDER BY s.started_at DESC;

-- VM pool status
SELECT hostname, ip_address, status, doctor_name, session_id, assigned_at
FROM vm_instances
ORDER BY hostname;

-- Recent audit logs
SELECT timestamp, action_type, resource_type, resource_id, ip_address
FROM audit_logs
ORDER BY timestamp DESC
LIMIT 20;

-- Patient count with studies
SELECT p.name, p.patient_id, COUNT(s.id) as study_count
FROM patients p
LEFT JOIN studies s ON s.patient_id = p.id
GROUP BY p.id
ORDER BY p.name;

-- Doctor assignments
SELECT d.name as doctor, p.name as patient, pa.assigned_at
FROM patient_assignments pa
JOIN doctors d ON d.id = pa.doctor_id
JOIN patients p ON p.id = pa.patient_id
ORDER BY d.name, p.name;
```

### Docker Logs

```bash
# Guacamole webapp logs
docker compose logs guacamole --tail 50

# guacd daemon logs (RDP connection details)
docker compose logs guacd --tail 50

# PostgreSQL logs
docker compose logs postgres --tail 50

# Keycloak logs
docker compose logs keycloak --tail 50
```

### Backend Logs

```bash
# If running with uvicorn directly
# Logs go to stdout -- look for these prefixes:
#   INFO:     - uvicorn access logs
#   INFO:app.services.session_monitor - timeout/cleanup events
#   INFO:app.services.dicom_watcher - DICOM ingestion events
#   WARNING:app.middleware.audit - audit logging failures
```

---

## Full State Reset

If you need to start completely fresh:

```bash
# Stop everything
docker compose down -v  # -v removes volumes (all data!)

# Restart infrastructure
docker compose up -d

# Re-run migrations
cd backend
alembic upgrade head

# Re-register VMs in the pool (admin API)
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/vm-pool \
  -d '{"hostname": "WIN-VM-01", "ip_address": "10.121.245.200"}'
```

> **Warning**: `docker compose down -v` deletes all data including Keycloak realm configuration, Guacamole users, and all application data. You will need to reconfigure Keycloak realm, clients, and users.

---

## Configuration Reference

Key settings from `backend/app/core/config.py` (override via `.env` file or environment variables):

| Setting | Default | Description |
|---------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/dental_portal` | Database connection |
| `KEYCLOAK_URL` | `http://10.121.245.146:8180` | Keycloak server |
| `KEYCLOAK_REALM` | `dental-portal` | Keycloak realm |
| `GUACAMOLE_URL` | `http://localhost:8080/guacamole` | Guacamole REST API |
| `WINRM_HOST` | `""` (empty = mock mode) | WinRM target host |
| `SESSION_IDLE_TIMEOUT` | 900 (15 min) | Idle timeout in seconds |
| `SESSION_HARD_TIMEOUT` | 3600 (60 min) | Hard timeout in seconds |
| `SESSION_CHECK_INTERVAL` | 60 | Monitor check interval |
| `MAX_CONCURRENT_SESSIONS` | 5 | Global session limit |
| `SMB_MOUNT_DRIVE` | `Z:` | Drive letter for DICOM share |
| `DICOM_WATCH_DIR` | `/mnt/dicom-export` | DICOM file watch directory |
