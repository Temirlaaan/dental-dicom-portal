import { Navigate, Route, Routes } from 'react-router-dom';
import AdminLayout from './components/AdminLayout';
import ProtectedRoute from './components/ProtectedRoute';
import AuthCallbackPage from './pages/AuthCallbackPage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import AssignmentsPage from './pages/admin/AssignmentsPage';
import AuditLogsPage from './pages/admin/AuditLogsPage';
import SessionsPage from './pages/admin/SessionsPage';
import SystemHealthPage from './pages/admin/SystemHealthPage';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
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
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default App;
