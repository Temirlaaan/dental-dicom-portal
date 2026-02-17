import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './api';
import type {
  Assignment,
  AuditLog,
  Doctor,
  HealthStatus,
  PaginatedList,
  Patient,
  Session,
} from '../types';

// ── Patients ─────────────────────────────────────────────────────────────────

interface PatientsParams {
  search?: string;
  limit?: number;
  offset?: number;
}

export function usePatients(params: PatientsParams = {}) {
  return useQuery<PaginatedList<Patient>>({
    queryKey: ['patients', params],
    queryFn: () =>
      api.get('/patients', { params }).then((r) => r.data),
  });
}

// ── Doctors ──────────────────────────────────────────────────────────────────

export function useDoctors() {
  return useQuery<Doctor[]>({
    queryKey: ['doctors'],
    queryFn: () => api.get('/doctors').then((r) => r.data),
  });
}

// ── Assignments ───────────────────────────────────────────────────────────────

interface AssignmentsParams {
  patient_id?: string;
  doctor_id?: string;
}

export function useAssignments(params: AssignmentsParams = {}) {
  return useQuery<Assignment[]>({
    queryKey: ['assignments', params],
    queryFn: () => api.get('/assignments', { params }).then((r) => r.data),
  });
}

export function useCreateAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { patient_id: string; doctor_id: string }) =>
      api.post('/assignments', body).then((r) => r.data as Assignment),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assignments'] }),
  });
}

export function useDeleteAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/assignments/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['assignments'] }),
  });
}

// ── Audit logs ────────────────────────────────────────────────────────────────

export interface AuditLogFilters {
  user_id?: string;
  action_type?: string;
  resource_type?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export function useAuditLogs(filters: AuditLogFilters = {}) {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== ''),
  );
  return useQuery<PaginatedList<AuditLog>>({
    queryKey: ['audit-logs', params],
    queryFn: () => api.get('/audit-logs', { params }).then((r) => r.data),
  });
}

export function buildExportUrl(filters: AuditLogFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== '') params.set(k, String(v));
  });
  const qs = params.toString();
  return `/api/audit-logs/export${qs ? `?${qs}` : ''}`;
}

// ── Health ────────────────────────────────────────────────────────────────────

export function useHealth() {
  return useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then((r) => r.data),
    refetchInterval: 30_000,
  });
}

// ── Sessions ──────────────────────────────────────────────────────────────────

export function useSessions() {
  return useQuery<Session[]>({
    queryKey: ['sessions'],
    queryFn: () => api.get('/sessions').then((r) => r.data),
    refetchInterval: 30_000,
    retry: false,
  });
}

export function useTerminateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/sessions/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });
}
