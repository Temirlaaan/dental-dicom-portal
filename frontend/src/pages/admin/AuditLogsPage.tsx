import { useState } from 'react';
import { buildExportUrl, useAuditLogs } from '../../services/adminApi';
import type { AuditLogFilters } from '../../services/adminApi';

const PAGE_SIZE = 50;

const ACTION_TYPES = ['', 'create', 'update', 'delete', 'session_terminated', 'session_idle_warning', 'session_orphan_cleanup'];

export default function AuditLogsPage() {
  const [filters, setFilters] = useState<AuditLogFilters>({});
  const [offset, setOffset] = useState(0);

  const activeFilters: AuditLogFilters = { ...filters, limit: PAGE_SIZE, offset };
  const { data, isLoading, isError } = useAuditLogs(activeFilters);

  const logs = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  function setFilter(key: keyof AuditLogFilters, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
    setOffset(0);
  }

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Audit Logs</h1>
        <a
          href={buildExportUrl(filters)}
          download="audit_logs.csv"
          style={{ padding: '8px 16px', background: '#16a34a', color: '#fff', borderRadius: 6, textDecoration: 'none', fontSize: 14, fontWeight: 500 }}
        >
          Export CSV
        </a>
      </div>

      {/* Filters */}
      <div style={{ background: '#fff', borderRadius: 8, padding: 16, marginBottom: 20, display: 'flex', flexWrap: 'wrap', gap: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>From</label>
          <input
            type="datetime-local"
            onChange={(e) => setFilter('date_from', e.target.value ? new Date(e.target.value).toISOString() : '')}
            style={{ padding: '6px 10px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 13 }}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>To</label>
          <input
            type="datetime-local"
            onChange={(e) => setFilter('date_to', e.target.value ? new Date(e.target.value).toISOString() : '')}
            style={{ padding: '6px 10px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 13 }}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>Action Type</label>
          <select
            onChange={(e) => setFilter('action_type', e.target.value)}
            style={{ padding: '6px 10px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 13, minWidth: 160 }}
          >
            {ACTION_TYPES.map((a) => (
              <option key={a} value={a}>{a || 'All actions'}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>User ID</label>
          <input
            type="text"
            placeholder="UUID…"
            onChange={(e) => setFilter('user_id', e.target.value)}
            style={{ padding: '6px 10px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 13, width: 220 }}
          />
        </div>
      </div>

      {isLoading && <p style={{ color: '#64748b' }}>Loading…</p>}
      {isError && <p style={{ color: '#dc2626' }}>Failed to load audit logs.</p>}

      <div style={{ background: '#fff', borderRadius: 8, overflow: 'auto', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 900 }}>
          <thead>
            <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
              {['Timestamp', 'User ID', 'Role', 'Action', 'Resource', 'Resource ID', 'IP'].map((h) => (
                <th key={h} style={{ padding: '12px 14px', fontSize: 12, fontWeight: 600, color: '#475569', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 && !isLoading && (
              <tr>
                <td colSpan={7} style={{ padding: 32, textAlign: 'center', color: '#94a3b8' }}>No audit logs found</td>
              </tr>
            )}
            {logs.map((log) => (
              <tr key={log.id} style={{ borderTop: '1px solid #f1f5f9' }}>
                <td style={{ padding: '10px 14px', fontSize: 12, color: '#64748b', whiteSpace: 'nowrap' }}>{new Date(log.timestamp).toLocaleString()}</td>
                <td style={{ padding: '10px 14px', fontSize: 12, maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={log.user_id ?? ''}>{log.user_id?.slice(0, 8) ?? '—'}</td>
                <td style={{ padding: '10px 14px', fontSize: 12 }}>{log.user_role ?? '—'}</td>
                <td style={{ padding: '10px 14px' }}>
                  <span style={{ background: '#eff6ff', color: '#1d4ed8', padding: '2px 8px', borderRadius: 10, fontSize: 12, fontWeight: 500 }}>{log.action_type}</span>
                </td>
                <td style={{ padding: '10px 14px', fontSize: 13 }}>{log.resource_type}</td>
                <td style={{ padding: '10px 14px', fontSize: 12, color: '#64748b', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={log.resource_id ?? ''}>{log.resource_id?.slice(0, 8) ?? '—'}</td>
                <td style={{ padding: '10px 14px', fontSize: 12, color: '#64748b' }}>{log.ip_address ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16 }}>
        <span style={{ fontSize: 13, color: '#64748b' }}>
          {total} total records
        </span>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <PagBtn label="«" onClick={() => setOffset(0)} disabled={currentPage === 1} />
          <PagBtn label="‹" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={currentPage === 1} />
          <span style={{ fontSize: 13, padding: '0 8px' }}>Page {currentPage} of {totalPages}</span>
          <PagBtn label="›" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={currentPage >= totalPages} />
          <PagBtn label="»" onClick={() => setOffset((totalPages - 1) * PAGE_SIZE)} disabled={currentPage >= totalPages} />
        </div>
      </div>
    </div>
  );
}

function PagBtn({ label, onClick, disabled }: { label: string; onClick: () => void; disabled: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{ padding: '5px 10px', border: '1px solid #e2e8f0', borderRadius: 6, background: disabled ? '#f8fafc' : '#fff', color: disabled ? '#cbd5e1' : '#374151', cursor: disabled ? 'not-allowed' : 'pointer', fontSize: 14 }}
    >
      {label}
    </button>
  );
}
