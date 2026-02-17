interface TimeoutWarningProps {
  show: boolean;
  type: 'idle' | 'hard';
  onExtend: () => void;
  onEnd: () => void;
}

export default function TimeoutWarning({ show, type, onExtend, onEnd }: TimeoutWarningProps) {
  if (!show) return null;

  const isHard = type === 'hard';

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: 32, maxWidth: 420, width: '90%',
        boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
        borderTop: `4px solid ${isHard ? '#dc2626' : '#d97706'}`,
      }}>
        <h3 style={{ margin: '0 0 12px', color: isHard ? '#dc2626' : '#92400e' }}>
          {isHard ? '⚠️ Session Ending Soon' : '💤 Idle Warning'}
        </h3>
        <p style={{ margin: '0 0 24px', color: '#475569', fontSize: 15, lineHeight: 1.5 }}>
          {isHard
            ? 'Your session will be automatically terminated in 10 minutes due to the session time limit.'
            : "You've been idle for 10 minutes. Click Extend to keep your session active."}
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button
            onClick={onEnd}
            style={{ padding: '9px 18px', border: '1px solid #e2e8f0', borderRadius: 7, background: '#fff', color: '#374151', cursor: 'pointer', fontSize: 14 }}
          >
            End Session
          </button>
          <button
            onClick={onExtend}
            style={{ padding: '9px 18px', background: isHard ? '#dc2626' : '#d97706', color: '#fff', border: 'none', borderRadius: 7, cursor: 'pointer', fontSize: 14, fontWeight: 600 }}
          >
            Extend Session
          </button>
        </div>
      </div>
    </div>
  );
}
