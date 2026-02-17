import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { usePatients } from '../services/adminApi';
import { useCreateSession } from '../services/doctorApi';
import { useSession } from '../contexts/SessionContext';
import type { Patient } from '../types';

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

  return (
    <div style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ margin: '0 0 20px', fontSize: 22, fontWeight: 700 }}>My Patients</h1>

      {/* Active session banner */}
      {activeSession && (
        <div style={{ background: '#dcfce7', border: '1px solid #86efac', borderRadius: 8, padding: '12px 16px', marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#16a34a', fontWeight: 500 }}>You have an active session.</span>
          <Link to={`/session/${activeSession.id}`} style={{ color: '#15803d', fontWeight: 600, textDecoration: 'none' }}>
            Return to Session →
          </Link>
        </div>
      )}

      {/* Error banner */}
      {launchError && (
        <div style={{ background: '#fef3c7', border: '1px solid #fbbf24', borderRadius: 8, padding: '12px 16px', marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#92400e', fontSize: 14 }}>{launchError}</span>
          <button onClick={() => setLaunchError(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#92400e', fontSize: 18, lineHeight: 1 }}>×</button>
        </div>
      )}

      {/* Filters */}
      <div style={{ background: '#fff', borderRadius: 8, padding: 16, marginBottom: 20, display: 'flex', flexWrap: 'wrap', gap: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <input
          type="text"
          placeholder="Search by patient name…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          style={{ padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: 7, fontSize: 14, minWidth: 240 }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label style={{ fontSize: 13, color: '#64748b' }}>Study date:</label>
          <input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }}
            style={{ padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 7, fontSize: 13 }} />
          <span style={{ color: '#94a3b8' }}>–</span>
          <input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setOffset(0); }}
            style={{ padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 7, fontSize: 13 }} />
        </div>
        {(search || dateFrom || dateTo) && (
          <button onClick={() => { setSearchInput(''); setSearch(''); setDateFrom(''); setDateTo(''); setOffset(0); }}
            style={{ padding: '7px 14px', background: '#f1f5f9', border: 'none', borderRadius: 7, fontSize: 13, cursor: 'pointer', color: '#475569' }}>
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      {isError && <p style={{ color: '#dc2626' }}>Failed to load patients.</p>}

      <div style={{ background: '#fff', borderRadius: 8, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
              {['Patient Name', 'Patient ID', 'Studies', 'Actions'].map((h) => (
                <th key={h} style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, color: '#475569' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={4} style={{ padding: 32, textAlign: 'center', color: '#94a3b8' }}>Loading patients…</td>
              </tr>
            )}
            {!isLoading && patients.length === 0 && (
              <tr>
                <td colSpan={4} style={{ padding: 32, textAlign: 'center', color: '#94a3b8' }}>
                  {search || dateFrom || dateTo ? 'No patients match your filters.' : 'No patients assigned to you yet.'}
                </td>
              </tr>
            )}
            {patients.map((p) => (
              <tr key={p.id} style={{ borderTop: '1px solid #f1f5f9' }}>
                <td style={{ padding: '13px 16px', fontWeight: 500 }}>{p.name}</td>
                <td style={{ padding: '13px 16px', fontSize: 13, color: '#64748b' }}>{p.patient_id}</td>
                <td style={{ padding: '13px 16px', fontSize: 13 }}>{p.study_count}</td>
                <td style={{ padding: '13px 16px' }}>
                  <button
                    onClick={() => handleLaunch(p.id)}
                    disabled={launchingId === p.id || !!activeSession}
                    title={activeSession ? 'End your current session first' : undefined}
                    style={{
                      padding: '6px 14px', background: '#3b82f6', color: '#fff', border: 'none',
                      borderRadius: 7, fontSize: 13, cursor: (launchingId === p.id || !!activeSession) ? 'not-allowed' : 'pointer',
                      opacity: (launchingId === p.id || !!activeSession) ? 0.6 : 1,
                    }}
                  >
                    {launchingId === p.id ? 'Launching…' : 'Open in DTX Studio'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16 }}>
          <span style={{ fontSize: 13, color: '#64748b' }}>{total} patients total</span>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <PagBtn label="‹" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={currentPage === 1} />
            <span style={{ fontSize: 13, padding: '0 8px' }}>Page {currentPage} of {totalPages}</span>
            <PagBtn label="›" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={currentPage >= totalPages} />
          </div>
        </div>
      )}
    </div>
  );
}

function PagBtn({ label, onClick, disabled }: { label: string; onClick: () => void; disabled: boolean }) {
  return (
    <button onClick={onClick} disabled={disabled}
      style={{ padding: '5px 12px', border: '1px solid #e2e8f0', borderRadius: 6, background: disabled ? '#f8fafc' : '#fff', color: disabled ? '#cbd5e1' : '#374151', cursor: disabled ? 'not-allowed' : 'pointer', fontSize: 14 }}>
      {label}
    </button>
  );
}
