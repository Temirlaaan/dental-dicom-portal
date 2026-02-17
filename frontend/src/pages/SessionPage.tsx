import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import TimeoutWarning from '../components/TimeoutWarning';
import { useSession } from '../contexts/SessionContext';
import { useEndSession, useSessionStatus } from '../services/doctorApi';

const GUACAMOLE_URL = (import.meta.env.VITE_GUACAMOLE_URL as string | undefined) ?? '/guacamole';
const IDLE_WARN_MS = 10 * 60 * 1000;   // 10 min idle warning
const HARD_WARN_MS = 50 * 60 * 1000;   // 50 min hard timeout warning

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
    : `${m}:${String(sec).padStart(2, '0')}`;
}

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { setActiveSession } = useSession();
  const endSession = useEndSession();
  const { data: session, isLoading, isError } = useSessionStatus(id);

  const [elapsed, setElapsed] = useState(0);
  const [idleMs, setIdleMs] = useState(0);
  const [warning, setWarning] = useState<'idle' | 'hard' | null>(null);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const lastActivityRef = useRef(Date.now());

  // Elapsed and idle timers
  useEffect(() => {
    const startTime = session ? new Date(session.started_at).getTime() : Date.now();
    const interval = setInterval(() => {
      const now = Date.now();
      setElapsed(now - startTime);
      setIdleMs(now - lastActivityRef.current);
    }, 1000);
    return () => clearInterval(interval);
  }, [session]);

  // Idle tracking
  const resetIdle = useCallback(() => { lastActivityRef.current = Date.now(); setIdleMs(0); }, []);
  useEffect(() => {
    window.addEventListener('mousemove', resetIdle);
    window.addEventListener('keydown', resetIdle);
    return () => {
      window.removeEventListener('mousemove', resetIdle);
      window.removeEventListener('keydown', resetIdle);
    };
  }, [resetIdle]);

  // Trigger warnings
  useEffect(() => {
    if (elapsed >= HARD_WARN_MS && warning !== 'hard') setWarning('hard');
    else if (idleMs >= IDLE_WARN_MS && warning !== 'idle' && warning !== 'hard') setWarning('idle');
  }, [elapsed, idleMs, warning]);

  // Clear active session on unmount if it matches
  useEffect(() => {
    return () => {
      setActiveSession((prev) => (prev?.id === id ? null : prev));
    };
  }, [id, setActiveSession]);

  async function handleEnd() {
    if (id) {
      try { await endSession.mutateAsync(id); } catch { /* ignore if API unavailable */ }
    }
    setActiveSession(null);
    navigate('/patients');
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b' }}>
        Loading session…
      </div>
    );
  }

  if (isError) {
    return (
      <div style={{ padding: 32 }}>
        <div style={{ background: '#fef3c7', border: '1px solid #fbbf24', borderRadius: 10, padding: 24, maxWidth: 600 }}>
          <h2 style={{ margin: '0 0 10px', color: '#92400e' }}>Session Not Found</h2>
          <p style={{ color: '#78350f', fontSize: 14, margin: '0 0 20px' }}>
            The sessions API is not yet available (Issue #3). The Guacamole session view will be fully functional once the session orchestration backend is implemented.
          </p>
          <button onClick={() => navigate('/patients')}
            style={{ padding: '8px 18px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 7, cursor: 'pointer' }}>
            Back to Patients
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Session toolbar */}
      <div style={{
        height: 46, background: '#1e293b', color: '#f1f5f9',
        display: 'flex', alignItems: 'center', padding: '0 20px', gap: 20, flexShrink: 0,
      }}>
        <span style={{ fontSize: 13, color: '#94a3b8' }}>
          Session: <strong style={{ color: '#f1f5f9' }}>{session?.patient_id?.slice(0, 8)}</strong>
        </span>
        <span style={{ fontSize: 13, color: '#94a3b8' }}>
          Duration: <strong style={{ color: '#f1f5f9' }}>{formatElapsed(elapsed)}</strong>
        </span>
        <span style={{ fontSize: 13 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#16a34a', display: 'inline-block', marginRight: 6 }} />
          Active
        </span>
        <div style={{ flex: 1 }} />
        <button
          onClick={() => setConfirmEnd(true)}
          style={{ padding: '6px 16px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
        >
          End Session
        </button>
      </div>

      {/* Guacamole iframe */}
      <iframe
        src={GUACAMOLE_URL}
        title="DTX Studio Session"
        allow="clipboard-read; clipboard-write"
        style={{ flex: 1, border: 'none', width: '100%' }}
      />

      {/* Timeout warning */}
      <TimeoutWarning
        show={warning !== null}
        type={warning ?? 'idle'}
        onExtend={() => { resetIdle(); setWarning(null); }}
        onEnd={handleEnd}
      />

      {/* End session confirmation */}
      {confirmEnd && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div style={{ background: '#fff', borderRadius: 12, padding: 28, maxWidth: 400, width: '90%', boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 12px' }}>End Session?</h3>
            <p style={{ color: '#475569', fontSize: 14, margin: '0 0 20px' }}>
              This will disconnect you from DTX Studio. Any unsaved work in the application may be lost.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setConfirmEnd(false)} style={{ padding: '8px 16px', border: '1px solid #e2e8f0', borderRadius: 6, background: '#fff', cursor: 'pointer' }}>Cancel</button>
              <button onClick={handleEnd} style={{ padding: '8px 16px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>End Session</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
