import { useState } from 'react';
import {
  useAssignments,
  useCreateAssignment,
  useDeleteAssignment,
  useDoctors,
  usePatients,
} from '../../services/adminApi';
import type { Doctor, Patient } from '../../types';

export default function AssignmentsPage() {
  const { data: patientsData, isLoading: patientsLoading } = usePatients({ limit: 200 });
  const { data: doctors, isLoading: doctorsLoading } = useDoctors();
  const { data: assignments, isLoading: assignmentsLoading } = useAssignments();
  const createAssignment = useCreateAssignment();
  const deleteAssignment = useDeleteAssignment();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [modalPatientId, setModalPatientId] = useState<string | null>(null);
  const [bulkModal, setBulkModal] = useState(false);
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const patients: Patient[] = patientsData?.items ?? [];
  const doctorsList: Doctor[] = doctors ?? [];
  const isLoading = patientsLoading || doctorsLoading || assignmentsLoading;

  function getDoctorForPatient(patientId: string): Doctor | undefined {
    const assignment = assignments?.find((a) => a.patient_id === patientId);
    return assignment ? doctorsList.find((d) => d.id === assignment.doctor_id) : undefined;
  }

  function getAssignmentId(patientId: string): string | undefined {
    return assignments?.find((a) => a.patient_id === patientId)?.id;
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selectedIds.size === patients.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(patients.map((p) => p.id)));
    }
  }

  async function handleAssign(patientId: string) {
    if (!selectedDoctorId) return;
    const existing = getAssignmentId(patientId);
    if (existing) await deleteAssignment.mutateAsync(existing);
    await createAssignment.mutateAsync({ patient_id: patientId, doctor_id: selectedDoctorId });
  }

  async function handleBulkAssign() {
    if (!selectedDoctorId) return;
    await Promise.all([...selectedIds].map((pid) => handleAssign(pid)));
    setSelectedIds(new Set());
    setBulkModal(false);
    setSelectedDoctorId('');
  }

  function openAssignModal(patientId: string) {
    setModalPatientId(patientId);
    setSelectedDoctorId(getDoctorForPatient(patientId)?.id ?? '');
  }

  return (
    <div style={{ padding: 32 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Patient Assignments</h1>
        {selectedIds.size > 0 && (
          <button
            onClick={() => { setBulkModal(true); setSelectedDoctorId(''); }}
            style={{ padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, fontSize: 14, cursor: 'pointer' }}
          >
            Bulk Assign ({selectedIds.size} selected)
          </button>
        )}
      </div>

      {isLoading && <p style={{ color: '#64748b' }}>Loading…</p>}

      <div style={{ background: '#fff', borderRadius: 8, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
              <th style={{ padding: '12px 16px', width: 40 }}>
                <input
                  type="checkbox"
                  checked={selectedIds.size === patients.length && patients.length > 0}
                  onChange={toggleAll}
                />
              </th>
              {['Patient Name', 'Patient ID', 'Studies', 'Current Doctor', 'Actions'].map((h) => (
                <th key={h} style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, color: '#475569' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {patients.length === 0 && !isLoading && (
              <tr>
                <td colSpan={6} style={{ padding: 32, textAlign: 'center', color: '#94a3b8' }}>No patients found</td>
              </tr>
            )}
            {patients.map((p) => {
              const doc = getDoctorForPatient(p.id);
              const assignmentId = getAssignmentId(p.id);
              return (
                <tr key={p.id} style={{ borderTop: '1px solid #f1f5f9', background: selectedIds.has(p.id) ? '#eff6ff' : undefined }}>
                  <td style={{ padding: '12px 16px' }}>
                    <input type="checkbox" checked={selectedIds.has(p.id)} onChange={() => toggleSelect(p.id)} />
                  </td>
                  <td style={{ padding: '12px 16px', fontWeight: 500 }}>{p.name}</td>
                  <td style={{ padding: '12px 16px', fontSize: 13, color: '#64748b' }}>{p.patient_id}</td>
                  <td style={{ padding: '12px 16px', fontSize: 13 }}>{p.study_count}</td>
                  <td style={{ padding: '12px 16px', fontSize: 14 }}>
                    {doc ? (
                      <span style={{ color: '#16a34a' }}>{doc.name}</span>
                    ) : (
                      <span style={{ color: '#94a3b8' }}>Unassigned</span>
                    )}
                  </td>
                  <td style={{ padding: '12px 16px', display: 'flex', gap: 8 }}>
                    <button
                      onClick={() => openAssignModal(p.id)}
                      style={{ padding: '5px 12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
                    >
                      {doc ? 'Reassign' : 'Assign'}
                    </button>
                    {assignmentId && (
                      <button
                        onClick={() => setConfirmDeleteId(assignmentId)}
                        style={{ padding: '5px 12px', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
                      >
                        Unassign
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Assign modal */}
      {modalPatientId && (
        <Modal title={`Assign Patient`} onClose={() => setModalPatientId(null)}>
          <DoctorSelect doctors={doctorsList} value={selectedDoctorId} onChange={setSelectedDoctorId} />
          <ModalButtons
            onCancel={() => setModalPatientId(null)}
            onConfirm={async () => {
              await handleAssign(modalPatientId);
              setModalPatientId(null);
              setSelectedDoctorId('');
            }}
            disabled={!selectedDoctorId}
            label="Assign"
          />
        </Modal>
      )}

      {/* Bulk assign modal */}
      {bulkModal && (
        <Modal title={`Bulk Assign ${selectedIds.size} Patients`} onClose={() => setBulkModal(false)}>
          <DoctorSelect doctors={doctorsList} value={selectedDoctorId} onChange={setSelectedDoctorId} />
          <ModalButtons onCancel={() => setBulkModal(false)} onConfirm={handleBulkAssign} disabled={!selectedDoctorId} label="Assign All" />
        </Modal>
      )}

      {/* Unassign confirm */}
      {confirmDeleteId && (
        <Modal title="Confirm Unassign" onClose={() => setConfirmDeleteId(null)}>
          <p style={{ color: '#475569', fontSize: 14, marginTop: 0 }}>Remove this patient-doctor assignment?</p>
          <ModalButtons
            onCancel={() => setConfirmDeleteId(null)}
            onConfirm={async () => {
              await deleteAssignment.mutateAsync(confirmDeleteId);
              setConfirmDeleteId(null);
            }}
            label="Unassign"
            danger
          />
        </Modal>
      )}
    </div>
  );
}

function Modal({ title, children }: { title: string; children: React.ReactNode; onClose?: () => void }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div style={{ background: '#fff', borderRadius: 12, padding: 28, maxWidth: 420, width: '90%', boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
        <h3 style={{ margin: '0 0 16px' }}>{title}</h3>
        {children}
      </div>
    </div>
  );
}

function DoctorSelect({ doctors, value, onChange }: { doctors: Doctor[]; value: string; onChange: (v: string) => void }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{ width: '100%', padding: '8px 10px', border: '1px solid #e2e8f0', borderRadius: 6, fontSize: 14, marginBottom: 20 }}
    >
      <option value="">Select a doctor…</option>
      {doctors.map((d) => (
        <option key={d.id} value={d.id}>{d.name} ({d.email})</option>
      ))}
    </select>
  );
}

function ModalButtons({ onCancel, onConfirm, disabled, label, danger }: {
  onCancel: () => void;
  onConfirm: () => void;
  disabled?: boolean;
  label: string;
  danger?: boolean;
}) {
  return (
    <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
      <button onClick={onCancel} style={{ padding: '8px 16px', border: '1px solid #e2e8f0', borderRadius: 6, background: '#fff', cursor: 'pointer' }}>Cancel</button>
      <button
        onClick={onConfirm}
        disabled={disabled}
        style={{ padding: '8px 16px', background: danger ? '#dc2626' : '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1 }}
      >
        {label}
      </button>
    </div>
  );
}
