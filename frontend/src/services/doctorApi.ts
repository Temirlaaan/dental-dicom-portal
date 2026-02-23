import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from './api';
import type { Session } from '../types';

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patientId: string) =>
      api.post('/sessions', { patient_id: patientId }).then((r) => r.data as Session),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
    retry: false,
  });
}

export function useEndSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/sessions/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });
}

export function useSessionStatus(id: string | undefined) {
  return useQuery<Session>({
    queryKey: ['sessions', id],
    queryFn: () => api.get(`/sessions/${id}`).then((r) => r.data),
    enabled: !!id,
    refetchInterval: 30_000,
    retry: false,
  });
}

export function useGuacamoleUrl(sessionId: string | undefined) {
  return useQuery<{ url: string }>({
    queryKey: ['guacamole-url', sessionId],
    queryFn: () => api.get(`/sessions/${sessionId}/guacamole-url`).then((r) => r.data),
    enabled: !!sessionId,
    retry: false,
  });
}
