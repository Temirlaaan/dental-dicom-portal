import { useHealth } from '../../services/adminApi';
import { Badge } from '../../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';

function StatusBadge({ ok }: { ok: boolean }) {
  return (
    <Badge variant={ok ? 'success' : 'destructive'} className="gap-1.5">
      <span className={`w-2 h-2 rounded-full ${ok ? 'bg-green-500' : 'bg-red-500'}`} />
      {ok ? 'Healthy' : 'Unavailable'}
    </Badge>
  );
}

export default function SystemHealthPage() {
  const { data, isLoading, isError, dataUpdatedAt } = useHealth();

  const apiOk = !isError && !!data;

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-900">System Health</h1>
        <span className="text-xs text-slate-500">
          {dataUpdatedAt ? `Last updated: ${new Date(dataUpdatedAt).toLocaleTimeString()}` : 'Checking…'}
        </span>
      </div>

      {isLoading && <p className="text-slate-500">Checking system status…</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs uppercase text-slate-500 font-semibold tracking-wide">API Backend</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusBadge ok={apiOk} />
            {data && (
              <div className="mt-2 text-sm text-slate-600">
                Version: <strong>{data.version}</strong>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs uppercase text-slate-500 font-semibold tracking-wide">Database</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusBadge ok={apiOk} />
            <div className="mt-2 text-sm text-slate-600">
              PostgreSQL connection via API health check.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs uppercase text-slate-500 font-semibold tracking-wide">Active Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">—</div>
            <div className="text-sm text-slate-400 mt-1">Sessions API pending (Issue #3)</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs uppercase text-slate-500 font-semibold tracking-wide">Keycloak</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusBadge ok={!!localStorage.getItem('access_token')} />
            <div className="mt-2 text-sm text-slate-600">
              Token present in session.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs uppercase text-slate-500 font-semibold tracking-wide">Guacamole</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-600">
            Remote desktop gateway at <code className="bg-slate-100 px-1.5 py-0.5 rounded">:8080</code>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-xs uppercase text-slate-500 font-semibold tracking-wide">DICOM Watcher</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-600">
            Filesystem watcher daemon managed by systemd (<code className="bg-slate-100 px-1.5 py-0.5 rounded">dicom-watcher.service</code>).
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
