export interface Patient {
  id: string;
  patient_id: string;
  name: string;
  created_at: string;
  study_count: number;
}

export interface Study {
  id: string;
  study_instance_uid: string;
  study_date: string;
  modality: string;
  referring_physician?: string;
  study_description?: string;
  series_description?: string;
  created_at: string;
}

export interface Doctor {
  id: string;
  keycloak_user_id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface Assignment {
  id: string;
  patient_id: string;
  doctor_id: string;
  assigned_by: string | null;
  assigned_at: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  user_id: string | null;
  user_role: string | null;
  action_type: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
}

export interface PaginatedList<T> {
  total: number;
  items: T[];
  limit: number;
  offset: number;
}

export interface Session {
  id: string;
  doctor_id: string;
  patient_id: string;
  status: 'creating' | 'active' | 'idle_warning' | 'terminating' | 'terminated';
  started_at: string;
  ended_at?: string;
}

export interface HealthStatus {
  status: string;
  version: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'doctor' | 'admin';
}
