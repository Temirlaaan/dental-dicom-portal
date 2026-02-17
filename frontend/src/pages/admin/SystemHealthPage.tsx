import { useHealth } from '../../services/adminApi';

function StatusBadge({ ok }: { ok: boolean }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 12px', borderRadius: 12, fontSize: 13, fontWeight: 600,
      background: ok ? '#dcfce7' : '#fee2e2',
      color: ok ? '#16a34a' : '#dc2626',
    }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: ok ? '#16a34a' : '#dc2626', display: 'inline-block' }} />
      {ok ? 'Healthy' : 'Unavailable'}
    </span>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: '#fff', borderRadius: 10, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', minWidth: 220 }}>
      <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>{title}</div>
      {children}
    </div>
  );
}

export default function SystemHealthPage() {
  const { data, isLoading, isError, dataUpdatedAt } = useHealth();

  const apiOk = !isError && !!data;

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>System Health</h1>
        <span style={{ fontSize: 12, color: '#94a3b8' }}>
          {dataUpdatedAt ? `Last updated: ${new Date(dataUpdatedAt).toLocaleTimeString()}` : 'Checking…'}
        </span>
      </div>

      {isLoading && <p style={{ color: '#64748b' }}>Checking system status…</p>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 20 }}>
        <Card title="API Backend">
          <StatusBadge ok={apiOk} />
          {data && (
            <div style={{ marginTop: 10, fontSize: 13, color: '#64748b' }}>
              Version: <strong>{data.version}</strong>
            </div>
          )}
        </Card>

        <Card title="Database">
          <StatusBadge ok={apiOk} />
          <div style={{ marginTop: 10, fontSize: 13, color: '#64748b' }}>
            PostgreSQL connection via API health check.
          </div>
        </Card>

        <Card title="Active Sessions">
          <div style={{ fontSize: 28, fontWeight: 700, color: '#1e293b' }}>—</div>
          <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>Sessions API pending (Issue #3)</div>
        </Card>

        <Card title="Keycloak">
          <StatusBadge ok={!!localStorage.getItem('access_token')} />
          <div style={{ marginTop: 10, fontSize: 13, color: '#64748b' }}>
            Token present in session.
          </div>
        </Card>

        <Card title="Guacamole">
          <div style={{ fontSize: 13, color: '#64748b' }}>
            Remote desktop gateway at{' '}
            <code style={{ background: '#f1f5f9', padding: '1px 5px', borderRadius: 3 }}>:8080</code>
          </div>
        </Card>

        <Card title="DICOM Watcher">
          <div style={{ fontSize: 13, color: '#64748b' }}>
            Filesystem watcher daemon managed by systemd (<code style={{ background: '#f1f5f9', padding: '1px 5px', borderRadius: 3 }}>dicom-watcher.service</code>).
          </div>
        </Card>
      </div>
    </div>
  );
}
