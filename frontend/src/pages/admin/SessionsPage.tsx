import { useState } from 'react';
import { useSessions, useTerminateSession } from '../../services/adminApi';
import type { Session } from '../../types';

function formatDuration(startedAt: string): string {
  const seconds = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return h > 0 ? `${h}h ${m}m` : m > 0 ? `${m}m ${s}s` : `${s}s`;
}

const STATUS_COLOR: Record<string, string> = {
  active: '#16a34a',
  idle_warning: '#d97706',
  creating: '#3b82f6',
  terminating: '#6b7280',
  terminated: '#dc2626',
};

export default function SessionsPage() {
  const { data, isLoading, isError, error } = useSessions();
  const terminate = useTerminateSession();
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const sessions: Session[] = data ?? [];
  const apiUnavailable = isError && (error as { response?: { status: number } })?.response?.status === 404;

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Active Sessions</h1>
        <span style={{ fontSize: 13, color: '#64748b' }}>Auto-refreshes every 30s</span>
      </div>

      {isLoading && <p style={{ color: '#64748b' }}>Loading sessions…</p>}

      {apiUnavailable && (
        <div style={{ background: '#fef3c7', border: '1px solid #fbbf24', borderRadius: 8, padding: 20, marginBottom: 24 }}>
          <strong>Sessions API not yet available.</strong>
          <p style={{ margin: '8px 0 0', color: '#78350f', fontSize: 14 }}>
            The sessions endpoint will be available once the session orchestration backend (Issue #3) is implemented.
          </p>
        </div>
      )}

      {isError && !apiUnavailable && (
        <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 8, padding: 16, marginBottom: 24 }}>
          Failed to load sessions.
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 8, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <thead>
          <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
            {['Doctor', 'Patient', 'Status', 'Started', 'Duration', 'Actions'].map((h) => (
              <th key={h} style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, color: '#475569' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sessions.length === 0 && !isLoading && (
            <tr>
              <td colSpan={6} style={{ padding: 32, textAlign: 'center', color: '#94a3b8' }}>
                {apiUnavailable ? 'No data — API unavailable' : 'No active sessions'}
              </td>
            </tr>
          )}
          {sessions.map((s) => (
            <tr key={s.id} style={{ borderTop: '1px solid #f1f5f9' }}>
              <td style={{ padding: '12px 16px', fontSize: 14 }}>{s.doctor_id}</td>
              <td style={{ padding: '12px 16px', fontSize: 14 }}>{s.patient_id}</td>
              <td style={{ padding: '12px 16px' }}>
                <span style={{ background: STATUS_COLOR[s.status] + '20', color: STATUS_COLOR[s.status], padding: '2px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600 }}>
                  {s.status}
                </span>
              </td>
              <td style={{ padding: '12px 16px', fontSize: 13, color: '#64748b' }}>{new Date(s.started_at).toLocaleString()}</td>
              <td style={{ padding: '12px 16px', fontSize: 13 }}>{formatDuration(s.started_at)}</td>
              <td style={{ padding: '12px 16px' }}>
                <button
                  disabled={s.status === 'terminated' || s.status === 'terminating'}
                  onClick={() => setConfirmId(s.id)}
                  style={{ padding: '5px 12px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer', opacity: s.status === 'terminated' ? 0.4 : 1 }}
                >
                  Force Terminate
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Confirm dialog */}
      {confirmId && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ background: '#fff', borderRadius: 12, padding: 28, maxWidth: 400, width: '90%', boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 12px' }}>Confirm Termination</h3>
            <p style={{ color: '#475569', fontSize: 14, margin: '0 0 20px' }}>
              Are you sure you want to force-terminate this session? The doctor will be disconnected immediately.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setConfirmId(null)} style={{ padding: '8px 16px', border: '1px solid #e2e8f0', borderRadius: 6, background: '#fff', cursor: 'pointer' }}>Cancel</button>
              <button
                onClick={() => { terminate.mutate(confirmId); setConfirmId(null); }}
                style={{ padding: '8px 16px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
              >
                Terminate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
