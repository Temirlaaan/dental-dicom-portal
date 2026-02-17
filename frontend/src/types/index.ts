export interface Patient {
  id: string;
  patientId: string;
  name: string;
  createdAt: string;
}

export interface Study {
  id: string;
  patientId: string;
  studyInstanceUid: string;
  studyDate: string;
  modality: string;
  description?: string;
}

export interface Session {
  id: string;
  doctorId: string;
  patientId: string;
  status: 'creating' | 'active' | 'idle_warning' | 'terminating' | 'closed';
  startedAt: string;
  endedAt?: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'doctor' | 'admin';
}
