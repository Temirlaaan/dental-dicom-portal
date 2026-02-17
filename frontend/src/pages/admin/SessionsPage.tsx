import { useState } from 'react';
import { useSessions, useTerminateSession } from '../../services/adminApi';
import type { Session } from '../../types';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';

function formatDuration(startedAt: string): string {
  const seconds = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return h > 0 ? `${h}h ${m}m` : m > 0 ? `${m}m ${s}s` : `${s}s`;
}

const STATUS_VARIANT: Record<string, 'default' | 'success' | 'warning' | 'destructive' | 'secondary'> = {
  active: 'success',
  idle_warning: 'warning',
  creating: 'default',
  terminating: 'secondary',
  terminated: 'destructive',
};

export default function SessionsPage() {
  const { data, isLoading, isError, error } = useSessions();
  const terminate = useTerminateSession();
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const sessions: Session[] = data ?? [];
  const apiUnavailable = isError && (error as { response?: { status: number } })?.response?.status === 404;

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Active Sessions</h1>
        <span className="text-sm text-slate-500">Auto-refreshes every 30s</span>
      </div>

      {isLoading && <p className="text-slate-500">Loading sessions…</p>}

      {apiUnavailable && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-5 mb-6">
          <strong className="text-amber-800">Sessions API not yet available.</strong>
          <p className="mt-2 text-sm text-amber-700">
            The sessions endpoint will be available once the session orchestration backend (Issue #3) is implemented.
          </p>
        </div>
      )}

      {isError && !apiUnavailable && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700">
          Failed to load sessions.
        </div>
      )}

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Doctor</TableHead>
              <TableHead>Patient</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sessions.length === 0 && !isLoading && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-slate-400 py-10">
                  {apiUnavailable ? 'No data — API unavailable' : 'No active sessions'}
                </TableCell>
              </TableRow>
            )}
            {sessions.map((s) => (
              <TableRow key={s.id}>
                <TableCell className="font-medium">{s.doctor_id}</TableCell>
                <TableCell>{s.patient_id}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANT[s.status] || 'default'}>
                    {s.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-slate-500">{new Date(s.started_at).toLocaleString()}</TableCell>
                <TableCell className="text-sm">{formatDuration(s.started_at)}</TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={s.status === 'terminated' || s.status === 'terminating'}
                    onClick={() => setConfirmId(s.id)}
                  >
                    Force Terminate
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Confirm dialog */}
      <Dialog open={!!confirmId} onOpenChange={() => setConfirmId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Termination</DialogTitle>
            <DialogDescription>
              Are you sure you want to force-terminate this session? The doctor will be disconnected immediately.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmId(null)}>Cancel</Button>
            <Button variant="destructive" onClick={() => { if (confirmId) terminate.mutate(confirmId); setConfirmId(null); }}>
              Terminate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
