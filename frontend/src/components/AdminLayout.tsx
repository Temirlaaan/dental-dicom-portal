import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const NAV_ITEMS = [
  { to: '/admin/sessions', label: 'Sessions' },
  { to: '/admin/assignments', label: 'Assignments' },
  { to: '/admin/audit-logs', label: 'Audit Logs' },
  { to: '/admin/health', label: 'System Health' },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      {/* Sidebar */}
      <aside style={{
        width: 220,
        background: '#1e293b',
        color: '#f1f5f9',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
      }}>
        <div style={{ padding: '20px 16px 12px', borderBottom: '1px solid #334155' }}>
          <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 4 }}>Admin Dashboard</div>
          <div style={{ fontWeight: 600, fontSize: 15 }}>{user?.name}</div>
        </div>

        <nav style={{ flex: 1, padding: '8px 0' }}>
          {NAV_ITEMS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                display: 'block',
                padding: '10px 20px',
                color: isActive ? '#fff' : '#94a3b8',
                background: isActive ? '#334155' : 'transparent',
                textDecoration: 'none',
                fontSize: 14,
                fontWeight: isActive ? 600 : 400,
                borderLeft: isActive ? '3px solid #3b82f6' : '3px solid transparent',
              })}
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: '12px 16px', borderTop: '1px solid #334155', display: 'flex', gap: 8 }}>
          <button
            onClick={() => navigate('/dashboard')}
            style={{ flex: 1, padding: '7px 0', background: '#334155', color: '#f1f5f9', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
          >
            Dashboard
          </button>
          <button
            onClick={logout}
            style={{ flex: 1, padding: '7px 0', background: '#475569', color: '#f1f5f9', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
          >
            Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, background: '#f8fafc', overflow: 'auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
