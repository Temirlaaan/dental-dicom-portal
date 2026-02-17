import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import TimeoutWarning from '../components/TimeoutWarning';
import { useSession } from '../contexts/SessionContext';
import { useEndSession, useSessionStatus } from '../services/doctorApi';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';

const GUACAMOLE_URL = (import.meta.env.VITE_GUACAMOLE_URL as string | undefined) ?? '/guacamole';
const IDLE_WARN_MS = 10 * 60 * 1000;
const HARD_WARN_MS = 50 * 60 * 1000;

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

  useEffect(() => {
    const startTime = session ? new Date(session.started_at).getTime() : Date.now();
    const interval = setInterval(() => {
      const now = Date.now();
      setElapsed(now - startTime);
      setIdleMs(now - lastActivityRef.current);
    }, 1000);
    return () => clearInterval(interval);
  }, [session]);

  const resetIdle = useCallback(() => { lastActivityRef.current = Date.now(); setIdleMs(0); }, []);
  useEffect(() => {
    window.addEventListener('mousemove', resetIdle);
    window.addEventListener('keydown', resetIdle);
    return () => {
      window.removeEventListener('mousemove', resetIdle);
      window.removeEventListener('keydown', resetIdle);
    };
  }, [resetIdle]);

  useEffect(() => {
    if (elapsed >= HARD_WARN_MS && warning !== 'hard') setWarning('hard');
    else if (idleMs >= IDLE_WARN_MS && warning !== 'idle' && warning !== 'hard') setWarning('idle');
  }, [elapsed, idleMs, warning]);

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
      <div className="flex items-center justify-center h-full text-slate-500">
        Loading session…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8">
        <Card className="max-w-xl border-amber-200">
          <CardHeader>
            <CardTitle className="text-amber-800">Session Not Found</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-amber-700">
              The sessions API is not yet available (Issue #3). The Guacamole session view will be fully functional once the session orchestration backend is implemented.
            </p>
            <Button variant="outline" onClick={() => navigate('/patients')}>
              Back to Patients
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Session toolbar */}
      <div className="h-12 bg-slate-900 text-slate-100 flex items-center px-5 gap-5 flex-shrink-0">
        <span className="text-sm text-slate-400">
          Session: <strong className="text-white">{session?.patient_id?.slice(0, 8)}</strong>
        </span>
        <span className="text-sm text-slate-400">
          Duration: <strong className="text-white">{formatElapsed(elapsed)}</strong>
        </span>
        <Badge variant="success" className="gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
          Active
        </Badge>
        <div className="flex-1" />
        <Button variant="destructive" size="sm" onClick={() => setConfirmEnd(true)}>
          End Session
        </Button>
      </div>

      {/* Guacamole iframe */}
      <iframe
        src={GUACAMOLE_URL}
        title="DTX Studio Session"
        allow="clipboard-read; clipboard-write"
        className="flex-1 border-none w-full"
      />

      {/* Timeout warning */}
      <TimeoutWarning
        show={warning !== null}
        type={warning ?? 'idle'}
        onExtend={() => { resetIdle(); setWarning(null); }}
        onEnd={handleEnd}
      />

      {/* End session confirmation */}
      <Dialog open={confirmEnd} onOpenChange={setConfirmEnd}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>End Session?</DialogTitle>
            <DialogDescription>
              This will disconnect you from DTX Studio. Any unsaved work in the application may be lost.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmEnd(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleEnd}>End Session</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
