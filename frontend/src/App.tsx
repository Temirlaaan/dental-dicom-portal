import { Navigate, Route, Routes } from 'react-router-dom';
import AdminLayout from './components/AdminLayout';
import DoctorLayout from './components/DoctorLayout';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuth } from './contexts/AuthContext';
import AuthCallbackPage from './pages/AuthCallbackPage';
import LoginPage from './pages/LoginPage';
import PatientsPage from './pages/PatientsPage';
import SessionPage from './pages/SessionPage';
import AssignmentsPage from './pages/admin/AssignmentsPage';
import AuditLogsPage from './pages/admin/AuditLogsPage';
import SessionsPage from './pages/admin/SessionsPage';
import SystemHealthPage from './pages/admin/SystemHealthPage';

function RoleRedirect() {
  const { user } = useAuth();
  return <Navigate to={user?.role === 'admin' ? '/admin' : '/patients'} replace />;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DoctorLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<RoleRedirect />} />
        <Route path="patients" element={<PatientsPage />} />
        <Route path="session/:id" element={<SessionPage />} />
      </Route>
      <Route
        path="/admin"
        element={
          <ProtectedRoute requiredRole="admin">
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/admin/sessions" replace />} />
        <Route path="sessions" element={<SessionsPage />} />
        <Route path="assignments" element={<AssignmentsPage />} />
        <Route path="audit-logs" element={<AuditLogsPage />} />
        <Route path="health" element={<SystemHealthPage />} />
      </Route>
    </Routes>
  );
}

export default App;
