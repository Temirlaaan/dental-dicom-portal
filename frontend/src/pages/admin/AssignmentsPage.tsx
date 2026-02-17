import { useState } from 'react';
import {
  useAssignments,
  useCreateAssignment,
  useDeleteAssignment,
  useDoctors,
  usePatients,
} from '../../services/adminApi';
import type { Doctor, Patient } from '../../types';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';

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
    <div className="p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Patient Assignments</h1>
        {selectedIds.size > 0 && (
          <Button onClick={() => { setBulkModal(true); setSelectedDoctorId(''); }}>
            Bulk Assign ({selectedIds.size} selected)
          </Button>
        )}
      </div>

      {isLoading && <p className="text-slate-500">Loading…</p>}

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <input
                  type="checkbox"
                  checked={selectedIds.size === patients.length && patients.length > 0}
                  onChange={toggleAll}
                  className="rounded"
                />
              </TableHead>
              <TableHead>Patient Name</TableHead>
              <TableHead>Patient ID</TableHead>
              <TableHead>Studies</TableHead>
              <TableHead>Current Doctor</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {patients.length === 0 && !isLoading && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-slate-400 py-10">No patients found</TableCell>
              </TableRow>
            )}
            {patients.map((p) => {
              const doc = getDoctorForPatient(p.id);
              const assignmentId = getAssignmentId(p.id);
              return (
                <TableRow key={p.id} className={selectedIds.has(p.id) ? 'bg-blue-50' : ''}>
                  <TableCell>
                    <input type="checkbox" checked={selectedIds.has(p.id)} onChange={() => toggleSelect(p.id)} className="rounded" />
                  </TableCell>
                  <TableCell className="font-medium text-slate-900">{p.name}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{p.patient_id}</Badge>
                  </TableCell>
                  <TableCell className="text-sm">{p.study_count}</TableCell>
                  <TableCell>
                    {doc ? (
                      <span className="text-green-700 font-medium text-sm">{doc.name}</span>
                    ) : (
                      <span className="text-slate-400 text-sm">Unassigned</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => openAssignModal(p.id)}>
                        {doc ? 'Reassign' : 'Assign'}
                      </Button>
                      {assignmentId && (
                        <Button size="sm" variant="outline" onClick={() => setConfirmDeleteId(assignmentId)} className="text-red-600 border-red-200 hover:bg-red-50">
                          Unassign
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Card>

      {/* Assign modal */}
      <Dialog open={!!modalPatientId} onOpenChange={() => setModalPatientId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Patient</DialogTitle>
          </DialogHeader>
          <select
            value={selectedDoctorId}
            onChange={(e) => setSelectedDoctorId(e.target.value)}
            className="w-full h-9 px-3 text-sm rounded-md border border-slate-200 mb-2"
          >
            <option value="">Select a doctor…</option>
            {doctorsList.map((d) => (
              <option key={d.id} value={d.id}>{d.name} ({d.email})</option>
            ))}
          </select>
          <DialogFooter>
            <Button variant="outline" onClick={() => setModalPatientId(null)}>Cancel</Button>
            <Button disabled={!selectedDoctorId} onClick={async () => {
              if (modalPatientId) { await handleAssign(modalPatientId); setModalPatientId(null); setSelectedDoctorId(''); }
            }}>Assign</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk assign modal */}
      <Dialog open={bulkModal} onOpenChange={setBulkModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bulk Assign {selectedIds.size} Patients</DialogTitle>
          </DialogHeader>
          <select
            value={selectedDoctorId}
            onChange={(e) => setSelectedDoctorId(e.target.value)}
            className="w-full h-9 px-3 text-sm rounded-md border border-slate-200 mb-2"
          >
            <option value="">Select a doctor…</option>
            {doctorsList.map((d) => (
              <option key={d.id} value={d.id}>{d.name} ({d.email})</option>
            ))}
          </select>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkModal(false)}>Cancel</Button>
            <Button disabled={!selectedDoctorId} onClick={handleBulkAssign}>Assign All</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unassign confirm */}
      <Dialog open={!!confirmDeleteId} onOpenChange={() => setConfirmDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Unassign</DialogTitle>
            <DialogDescription>Remove this patient-doctor assignment?</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDeleteId(null)}>Cancel</Button>
            <Button variant="destructive" onClick={async () => {
              if (confirmDeleteId) { await deleteAssignment.mutateAsync(confirmDeleteId); setConfirmDeleteId(null); }
            }}>Unassign</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
