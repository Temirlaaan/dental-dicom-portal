import { useState } from 'react';
import { buildExportUrl, useAuditLogs } from '../../services/adminApi';
import type { AuditLogFilters } from '../../services/adminApi';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent } from '../../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';

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
    <div className="p-8">
      <div className="flex justify-between items-center mb-5">
        <h1 className="text-2xl font-bold text-slate-900">Audit Logs</h1>
        <a href={buildExportUrl(filters)} download="audit_logs.csv">
          <Button variant="success">Export CSV</Button>
        </a>
      </div>

      <Card className="mb-5">
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-500 font-medium">From</label>
              <Input
                type="datetime-local"
                onChange={(e) => setFilter('date_from', e.target.value ? new Date(e.target.value).toISOString() : '')}
                className="w-48 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-500 font-medium">To</label>
              <Input
                type="datetime-local"
                onChange={(e) => setFilter('date_to', e.target.value ? new Date(e.target.value).toISOString() : '')}
                className="w-48 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-500 font-medium">Action Type</label>
              <select
                onChange={(e) => setFilter('action_type', e.target.value)}
                className="h-9 w-40 px-3 text-sm rounded-md border border-slate-200"
              >
                {ACTION_TYPES.map((a) => (
                  <option key={a} value={a}>{a || 'All actions'}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-500 font-medium">User ID</label>
              <Input
                type="text"
                placeholder="UUID…"
                onChange={(e) => setFilter('user_id', e.target.value)}
                className="w-56 text-sm"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoading && <p className="text-slate-500">Loading…</p>}
      {isError && <p className="text-red-600">Failed to load audit logs.</p>}

      <Card>
        <div className="overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="whitespace-nowrap">Timestamp</TableHead>
                <TableHead className="whitespace-nowrap">User ID</TableHead>
                <TableHead className="whitespace-nowrap">Role</TableHead>
                <TableHead className="whitespace-nowrap">Action</TableHead>
                <TableHead className="whitespace-nowrap">Resource</TableHead>
                <TableHead className="whitespace-nowrap">Resource ID</TableHead>
                <TableHead className="whitespace-nowrap">IP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.length === 0 && !isLoading && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-slate-400 py-10">No audit logs found</TableCell>
                </TableRow>
              )}
              {logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="text-xs text-slate-500 whitespace-nowrap">{new Date(log.timestamp).toLocaleString()}</TableCell>
                  <TableCell className="text-xs max-w-32 truncate" title={log.user_id ?? ''}>{log.user_id?.slice(0, 8) ?? '—'}</TableCell>
                  <TableCell className="text-xs">{log.user_role ?? '—'}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{log.action_type}</Badge>
                  </TableCell>
                  <TableCell className="text-sm">{log.resource_type}</TableCell>
                  <TableCell className="text-xs text-slate-500 max-w-28 truncate" title={log.resource_id ?? ''}>{log.resource_id?.slice(0, 8) ?? '—'}</TableCell>
                  <TableCell className="text-xs text-slate-500">{log.ip_address ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <div className="flex items-center justify-between mt-4">
        <span className="text-sm text-slate-500">{total} total records</span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setOffset(0)} disabled={currentPage === 1}>«</Button>
          <Button variant="outline" size="sm" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={currentPage === 1}>‹</Button>
          <span className="text-sm px-2">Page {currentPage} of {totalPages}</span>
          <Button variant="outline" size="sm" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={currentPage >= totalPages}>›</Button>
          <Button variant="outline" size="sm" onClick={() => setOffset((totalPages - 1) * PAGE_SIZE)} disabled={currentPage >= totalPages}>»</Button>
        </div>
      </div>
    </div>
  );
}
