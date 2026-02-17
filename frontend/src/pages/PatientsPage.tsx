import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { usePatients } from '../services/adminApi';
import { useCreateSession } from '../services/doctorApi';
import { useSession } from '../contexts/SessionContext';
import type { Patient } from '../types';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';

const PAGE_SIZE = 20;

export default function PatientsPage() {
  const navigate = useNavigate();
  const { activeSession, setActiveSession } = useSession();
  const createSession = useCreateSession();

  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [offset, setOffset] = useState(0);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [launchingId, setLaunchingId] = useState<string | null>(null);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput); setOffset(0); }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const params = {
    ...(search ? { search } : {}),
    ...(dateFrom ? { study_date_from: dateFrom } : {}),
    ...(dateTo ? { study_date_to: dateTo } : {}),
    limit: PAGE_SIZE,
    offset,
  };

  const { data, isLoading, isError } = usePatients(params);
  const patients: Patient[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  async function handleLaunch(patientId: string) {
    setLaunchError(null);
    setLaunchingId(patientId);
    try {
      const session = await createSession.mutateAsync(patientId);
      setActiveSession(session);
      navigate(`/session/${session.id}`);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404 || status === undefined) {
        setLaunchError('Session API not yet available (Issue #3). The sessions endpoint is pending implementation.');
      } else if (status === 429) {
        setLaunchError('Session limit reached. Please end an existing session before starting a new one.');
      } else {
        setLaunchError('Failed to launch session. Please try again.');
      }
    } finally {
      setLaunchingId(null);
    }
  }

  const hasFilters = !!(search || dateFrom || dateTo);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900 mb-6">My Patients</h1>

      {/* Active session banner */}
      {activeSession && (
        <div className="mb-4 flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-4 py-3">
          <span className="text-green-800 font-medium text-sm">You have an active session.</span>
          <Link to={`/session/${activeSession.id}`} className="text-green-700 font-semibold text-sm hover:underline">
            Return to Session →
          </Link>
        </div>
      )}

      {/* Error banner */}
      {launchError && (
        <div className="mb-4 flex items-center justify-between bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
          <span className="text-amber-800 text-sm">{launchError}</span>
          <button onClick={() => setLaunchError(null)} className="text-amber-700 text-lg leading-none ml-4 hover:text-amber-900">×</button>
        </div>
      )}

      {/* Filters */}
      <Card className="mb-5">
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-3 items-center">
            <Input
              type="text"
              placeholder="Search by patient name…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="min-w-60"
            />
            <div className="flex items-center gap-2">
              <label className="text-sm text-slate-500">Study date:</label>
              <Input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }} className="w-36" />
              <span className="text-slate-400">–</span>
              <Input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setOffset(0); }} className="w-36" />
            </div>
            {hasFilters && (
              <Button variant="secondary" size="sm" onClick={() => { setSearchInput(''); setSearch(''); setDateFrom(''); setDateTo(''); setOffset(0); }}>
                Clear filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      {isError && <p className="text-red-600 mb-4 text-sm">Failed to load patients.</p>}

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Patient Name</TableHead>
              <TableHead>Patient ID</TableHead>
              <TableHead>Studies</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-slate-400 py-10">Loading patients…</TableCell>
              </TableRow>
            )}
            {!isLoading && patients.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-slate-400 py-10">
                  {hasFilters ? 'No patients match your filters.' : 'No patients assigned to you yet.'}
                </TableCell>
              </TableRow>
            )}
            {patients.map((p) => (
              <TableRow key={p.id}>
                <TableCell className="font-medium text-slate-900">{p.name}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{p.patient_id}</Badge>
                </TableCell>
                <TableCell>{p.study_count}</TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    onClick={() => handleLaunch(p.id)}
                    disabled={launchingId === p.id || !!activeSession}
                    title={activeSession ? 'End your current session first' : undefined}
                  >
                    {launchingId === p.id ? 'Launching…' : 'Open in DTX Studio'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-slate-500">{total} patients total</span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={currentPage === 1}>‹</Button>
            <span className="text-sm text-slate-600 px-2">Page {currentPage} of {totalPages}</span>
            <Button variant="outline" size="sm" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={currentPage >= totalPages}>›</Button>
          </div>
        </div>
      )}
    </div>
  );
}
