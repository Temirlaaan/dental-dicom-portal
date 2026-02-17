import { useAuth } from '../contexts/AuthContext';

export default function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span>
            {user?.name} ({user?.role})
          </span>
          <button onClick={logout} style={{ padding: '6px 16px', cursor: 'pointer' }}>
            Logout
          </button>
        </div>
      </div>
      <p>Patient list and session management will be implemented in upcoming tasks.</p>
      {user?.role === 'admin' && (
        <p style={{ color: '#666', marginTop: '10px' }}>
          Admin dashboard features (session monitoring, assignments, audit logs) coming soon.
        </p>
      )}
    </div>
  );
}
