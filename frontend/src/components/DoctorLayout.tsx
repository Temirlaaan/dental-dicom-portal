import { Link, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useSession } from '../contexts/SessionContext';

export default function DoctorLayout() {
  const { user, logout } = useAuth();
  const { activeSession } = useSession();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      {/* Header */}
      <header style={{
        height: 52, background: '#1e293b', color: '#f1f5f9',
        display: 'flex', alignItems: 'center', padding: '0 24px',
        gap: 16, flexShrink: 0, boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
      }}>
        <Link to="/patients" style={{ color: '#f1f5f9', textDecoration: 'none', fontWeight: 700, fontSize: 16 }}>
          Dental DICOM Portal
        </Link>

        <div style={{ flex: 1 }} />

        {activeSession && (
          <Link
            to={`/session/${activeSession.id}`}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '5px 12px', borderRadius: 20,
              background: '#16a34a', color: '#fff',
              textDecoration: 'none', fontSize: 13, fontWeight: 600,
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#86efac', display: 'inline-block' }} />
            Active Session
          </Link>
        )}

        <span style={{ fontSize: 14, color: '#94a3b8' }}>{user?.name}</span>

        <button
          onClick={logout}
          style={{ padding: '5px 14px', background: '#334155', color: '#f1f5f9', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
        >
          Logout
        </button>
      </header>

      {/* Page content */}
      <main style={{ flex: 1, overflow: 'auto', background: '#f8fafc' }}>
        <Outlet />
      </main>
    </div>
  );
}
