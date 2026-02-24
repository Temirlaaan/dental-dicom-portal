# Frontend Architecture

**Framework**: React 19 + TypeScript 5.9
**Build**: Vite 7.x
**UI**: Radix UI primitives + Tailwind CSS 4.x
**Data**: TanStack React Query 5.x + Axios
**Routing**: React Router DOM 7.x

## Routes

| Path | Component | Layout | Auth | Description |
|------|-----------|--------|------|-------------|
| `/login` | `LoginPage` | None | Public | Keycloak login redirect |
| `/auth/callback` | `AuthCallbackPage` | None | Public | OAuth callback handler |
| `/` | `RoleRedirect` | `DoctorLayout` | Any | Redirects to `/patients` (doctor) or `/admin` (admin) |
| `/patients` | `PatientsPage` | `DoctorLayout` | Any | Patient list with search/filter |
| `/session/:id` | `SessionPage` | `DoctorLayout` | Any | RDP session viewer |
| `/admin` | Redirect | `AdminLayout` | Admin | Redirects to `/admin/sessions` |
| `/admin/sessions` | `SessionsPage` | `AdminLayout` | Admin | Session management |
| `/admin/assignments` | `AssignmentsPage` | `AdminLayout` | Admin | Patient-doctor assignments |
| `/admin/audit-logs` | `AuditLogsPage` | `AdminLayout` | Admin | Audit log viewer |
| `/admin/health` | `SystemHealthPage` | `AdminLayout` | Admin | System health dashboard |

Route definitions: `frontend/src/App.tsx`

---

## Component Hierarchy

```
<AuthProvider>
  <SessionProvider>
    <QueryClientProvider>
      <BrowserRouter>
        <Routes>
          <LoginPage />
          <AuthCallbackPage />
          <ProtectedRoute>
            <DoctorLayout>              <!-- sidebar + Outlet -->
              <PatientsPage />
              <SessionPage>
                <GuacamoleDisplay />    <!-- WebSocket RDP canvas -->
                <TimeoutWarning />
              </SessionPage>
            </DoctorLayout>
          </ProtectedRoute>
          <ProtectedRoute requiredRole="admin">
            <AdminLayout>               <!-- sidebar + Outlet -->
              <SessionsPage />
              <AssignmentsPage />
              <AuditLogsPage />
              <SystemHealthPage />
            </AdminLayout>
          </ProtectedRoute>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </SessionProvider>
</AuthProvider>
```

---

## Context Providers

### AuthContext

**File**: `frontend/src/contexts/AuthContext.tsx`

Manages the full Keycloak OIDC authentication lifecycle:

| Field | Type | Description |
|-------|------|-------------|
| `user` | `User \| null` | Current user (id, name, email, role) |
| `accessToken` | `string \| null` | JWT access token |
| `refreshToken` | `string \| null` | Refresh token |
| `isAuthenticated` | `boolean` | Whether user is logged in |
| `isLoading` | `boolean` | Initial auth check in progress |

| Method | Description |
|--------|-------------|
| `login()` | Redirects to Keycloak authorization URL |
| `logout()` | Clears tokens, redirects to Keycloak logout |
| `handleCallback(code)` | Exchanges auth code for tokens, fetches user profile |

**Token management**:
- Tokens stored in `sessionStorage` (primary) and `localStorage` (for Axios interceptor)
- Auto-refreshes access token every 4 minutes via `POST /api/auth/refresh`
- On mount, attempts to restore session from `sessionStorage`

### SessionContext

**File**: `frontend/src/contexts/SessionContext.tsx`

Tracks the currently active RDP session in the doctor view:

| Field | Type | Description |
|-------|------|-------------|
| `activeSession` | `Session \| null` | Currently active session |
| `setActiveSession` | `SetStateAction` | Update active session |

---

## API Services

### Base Client

**File**: `frontend/src/services/api.ts`

Axios instance with:
- Base URL from `VITE_API_URL` env var (default: `/api`)
- Request interceptor adds `Authorization: Bearer <token>` from `localStorage`

### Doctor API Hooks

**File**: `frontend/src/services/doctorApi.ts`

React Query hooks for session management:

| Hook | Type | Endpoint | Description |
|------|------|----------|-------------|
| `useCreateSession()` | Mutation | `POST /sessions` | Create new RDP session |
| `useEndSession()` | Mutation | `DELETE /sessions/:id` | Terminate a session |
| `useSessionStatus(id)` | Query | `GET /sessions/:id` | Poll session status (30s interval) |
| `useGuacamoleUrl(id)` | Query | `GET /sessions/:id/guacamole-url` | Fetch Guacamole connection params |

`useGuacamoleUrl` is only enabled when the session status is `active` and uses `staleTime: Infinity` to avoid refetching.

---

## Key Components

### GuacamoleDisplay

**File**: `frontend/src/components/GuacamoleDisplay.tsx`

Canvas-based RDP viewer using `guacamole-common-js`. Replaces the previous iframe approach.

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `token` | `string` | Guacamole auth token |
| `connectionId` | `string` | Guacamole connection identifier |
| `datasource` | `string` | Data source name (e.g., `"postgresql"`) |
| `onStateChange` | `(state, label) => void` | Connection state callback |
| `onError` | `(message) => void` | Error callback |

**Connection lifecycle**:

1. Creates `Guacamole.WebSocketTunnel` to `/guacamole/websocket-tunnel`
   - Protocol auto-selected: `ws:` or `wss:` based on page protocol
   - Falls back to `Guacamole.HTTPTunnel` if WebSocket unavailable
2. Creates `Guacamole.Client` with the tunnel
3. Appends display `<canvas>` element to container div
4. Sets up keyboard input (`Guacamole.Keyboard` on `document`)
5. Sets up mouse input (`Guacamole.Mouse` on display element)
6. Connects with query params: `token`, `GUAC_ID`, `GUAC_TYPE=c`, `GUAC_DATA_SOURCE`, `GUAC_WIDTH`, `GUAC_HEIGHT`, `GUAC_DPI`
7. On connect, scales display to fit container (never upscales)
8. On window resize, rescales and sends new size to server

**State labels**: `Idle (0)`, `Connecting (1)`, `Waiting (2)`, `Connected (3)`, `Disconnecting (4)`, `Disconnected (5)`

**Cleanup**: On unmount, disconnects client, removes keyboard/mouse listeners, clears container.

### ProtectedRoute

**File**: `frontend/src/components/ProtectedRoute.tsx`

Route guard that:
- Shows loading spinner while `isLoading` is true
- Redirects to `/login` if not authenticated
- Checks `requiredRole` prop against user role (redirects to `/` if insufficient)

### TimeoutWarning

**File**: `frontend/src/components/TimeoutWarning.tsx`

Modal dialog shown when session approaches timeout:
- **Idle warning**: "You've been idle for 10 minutes" -- yellow border
- **Hard warning**: "Session ending soon" -- red border
- Actions: "Extend Session" or "End Session"

### Layout Components

- **DoctorLayout** (`frontend/src/components/DoctorLayout.tsx`): Sidebar nav + `<Outlet>` for doctor pages
- **AdminLayout** (`frontend/src/components/AdminLayout.tsx`): Sidebar nav + `<Outlet>` for admin pages

---

## TypeScript Types

**File**: `frontend/src/types/index.ts`

| Type | Fields | Description |
|------|--------|-------------|
| `Patient` | id, patient_id, name, created_at, study_count | Patient list item |
| `Study` | id, study_instance_uid, study_date, modality, ... | DICOM study |
| `Doctor` | id, keycloak_user_id, name, email, created_at | Doctor profile |
| `Assignment` | id, patient_id, doctor_id, assigned_by, assigned_at | Patient-doctor link |
| `AuditLog` | id, timestamp, user_id, action_type, resource_type, details, ... | Audit entry |
| `Session` | id, doctor_id, patient_id, status, started_at, ended_at | RDP session |
| `HealthStatus` | status, version | Health check response |
| `User` | id, name, email, role | Authenticated user |
| `PaginatedList<T>` | total, items, limit, offset | Generic paginated response |

Session status union type: `'creating' | 'active' | 'idle_warning' | 'terminating' | 'terminated'`

---

## UI Component Library

The project uses [shadcn/ui](https://ui.shadcn.com/) patterns with:
- **Radix UI** primitives: Dialog, Label, Separator, Slot
- **Tailwind CSS 4** via `@tailwindcss/vite` plugin
- **class-variance-authority (cva)** for variant styling
- **clsx + tailwind-merge** for conditional class composition
- **lucide-react** for icons

UI components live in `frontend/src/components/ui/` (Button, Badge, Card, Dialog, etc.).

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `/api` | Backend API base URL |
| `VITE_KEYCLOAK_URL` | `http://10.121.245.146:8180` | Keycloak server URL |
| `VITE_KEYCLOAK_REALM` | `dental-portal` | Keycloak realm name |
| `VITE_KEYCLOAK_CLIENT_ID` | `dental-frontend` | Keycloak client ID |

---

## Vite Dev Proxy

**File**: `frontend/vite.config.ts`

Two proxy rules for development:

```js
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
  '/guacamole': {
    target: 'http://localhost:8080',
    changeOrigin: true,
    ws: true,  // WebSocket proxy for Guacamole tunnel
  },
}
```

This means:
- `/api/*` requests -> FastAPI backend on port 8000
- `/guacamole/*` requests (including WebSocket) -> Guacamole webapp on port 8080

---

## Key Flows

### Authentication Flow

1. User visits any protected route
2. `ProtectedRoute` checks `AuthContext.isAuthenticated`
3. If not authenticated, redirects to `/login`
4. `LoginPage` calls `AuthContext.login()` -> redirects to Keycloak
5. User authenticates at Keycloak -> redirects to `/auth/callback?code=xxx`
6. `AuthCallbackPage` calls `AuthContext.handleCallback(code)`:
   - Exchanges code via `GET /api/auth/callback`
   - Stores tokens in sessionStorage/localStorage
   - Fetches user profile via `GET /api/auth/me`
7. User is redirected to their role-appropriate landing page

### Session Launch Flow

1. Doctor views patient list on `/patients`
2. Clicks "Start Session" for a patient
3. `useCreateSession()` mutation fires `POST /api/sessions { patient_id }`
4. On success, `setActiveSession(session)` and navigate to `/session/:id`
5. `SessionPage` polls session status via `useSessionStatus(id)`
6. When `status === 'active'`, `useGuacamoleUrl(id)` fetches connection params
7. `GuacamoleDisplay` renders with `token`, `connectionId`, `datasource`
8. WebSocket tunnel connects, remote desktop appears on canvas

### Timeout Protection

1. `SessionPage` tracks elapsed time and idle time
2. `IDLE_WARN_MS = 10 * 60 * 1000` (10 min) -- triggers idle warning
3. `HARD_WARN_MS = 50 * 60 * 1000` (50 min) -- triggers hard timeout warning
4. User activity (mousemove/keydown) resets idle timer
5. `TimeoutWarning` dialog offers "Extend" or "End Session"
6. "Extend" calls `POST /api/sessions/:id/extend` and resets timers
7. "End Session" calls `DELETE /api/sessions/:id` and navigates to `/patients`
