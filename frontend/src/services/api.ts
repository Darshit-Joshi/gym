import axios from 'axios';
import type {
  AuthResponse,
  Client,
  Exercise,
  WorkoutSession,
  ProgressPhoto,
  PhotoPose,
  TrainerNote,
  TrainerDashboardData,
  DailyAttendanceResponse,
  AttendanceRecord,
  AttendanceHistorySummary,
  MonthlyAttendanceOverviewResponse,
  MembershipPlan,
  PaginatedFees,
  PaginatedMemberships,
  ClientFeeAccount,
  FeeRecord,
  FeeSummary,
  PaginatedNotifications,
  AppNotification,
  FeeStatus,
  PaymentMethod,
  DayExerciseDetail,
  PaginatedClients,
} from '../types';
import { prepareImageForUpload } from '../utils/prepareImage';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token from localStorage to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('gym_auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 Unauthorized globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('gym_auth_token');
      localStorage.removeItem('gym_user');
      if (window.location.pathname !== '/login' && window.location.pathname !== '/setup') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const authService = {
  registerTrainer: async (data: { name: string; email: string; password: string; phone?: string }): Promise<AuthResponse> => {
    const res = await api.post<AuthResponse>('/auth/register-trainer', data);
    return res.data;
  },
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const res = await api.post<AuthResponse>('/auth/login', { email, password });
    return res.data;
  },
  logout: async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // Ignored
    } finally {
      localStorage.removeItem('gym_auth_token');
      localStorage.removeItem('gym_user');
    }
  },
  /** Whether new trainers may sign up (the server can close registration). */
  getSetupStatus: async (): Promise<{ can_register_trainer: boolean }> => {
    const res = await api.get<{ can_register_trainer: boolean }>('/auth/setup-status');
    return res.data;
  },
  changePassword: async (current_password: string, new_password: string) => {
    const res = await api.post('/auth/change-password', { current_password, new_password });
    return res.data;
  },
};

export const dashboardService = {
  getTrainerDashboard: async (): Promise<TrainerDashboardData> => {
    const res = await api.get<TrainerDashboardData>('/dashboard/trainer');
    return res.data;
  },
};

export const clientService = {
  /** Paginated list. `status: 'current'` means everyone not archived. */
  getClients: async (params: {
    search?: string;
    status?: string;
    goal?: string;
    page: number;
    page_size: number;
  }): Promise<PaginatedClients> => {
    const res = await api.get<PaginatedClients>('/clients', { params });
    return res.data;
  },
  /** Every client not archived, sorted by name (for pickers). */
  getRoster: async (): Promise<Client[]> => {
    const res = await api.get<Client[]>('/clients', { params: { status: 'current' } });
    return [...res.data].sort((a, b) => a.name.localeCompare(b.name));
  },
  getClient: async (id: number): Promise<Client> => {
    const res = await api.get<Client>(`/clients/${id}`);
    return res.data;
  },
  createClient: async (data: any): Promise<Client> => {
    const res = await api.post<Client>('/clients', data);
    return res.data;
  },
  updateClient: async (id: number, data: any): Promise<Client> => {
    const res = await api.put<Client>(`/clients/${id}`, data);
    return res.data;
  },
  archiveClient: async (id: number): Promise<{ message: string }> => {
    const res = await api.post(`/clients/${id}/archive`);
    return res.data;
  },
  /** Only works for archived clients: removes the client and all of their records. */
  deleteClientPermanently: async (id: number): Promise<{ message: string }> => {
    const res = await api.delete(`/clients/${id}/permanent`);
    return res.data;
  },
  uploadPhoto: async (clientId: number, file: File): Promise<{ message: string; profile_photo: string; photo_url: string }> => {
    const formData = new FormData();
    formData.append('file', await prepareImageForUpload(file));
    const res = await api.post<{ message: string; profile_photo: string; photo_url: string }>(`/clients/${clientId}/photo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  deletePhoto: async (clientId: number): Promise<{ message: string }> => {
    const res = await api.delete<{ message: string }>(`/clients/${clientId}/photo`);
    return res.data;
  },
};

export const exerciseService = {
  getExercises: async (params?: {
    muscle_group?: string;
    equipment?: string;
    difficulty?: string;
    search?: string;
  }): Promise<Exercise[]> => {
    const res = await api.get<Exercise[]>('/exercises', { params });
    return res.data;
  },
  createExercise: async (data: Partial<Exercise>): Promise<Exercise> => {
    const res = await api.post<Exercise>('/exercises', data);
    return res.data;
  },
  updateExercise: async (id: number, data: Partial<Exercise>): Promise<Exercise> => {
    const res = await api.put<Exercise>(`/exercises/${id}`, data);
    return res.data;
  },
  deleteExercise: async (id: number) => {
    const res = await api.delete(`/exercises/${id}`);
    return res.data;
  },
};

export const sessionService = {
  getSessions: async (params?: { client_id?: number; session_date?: string; limit?: number }): Promise<WorkoutSession[]> => {
    const res = await api.get<WorkoutSession[]>('/sessions', { params });
    return res.data;
  },
  /** Store the exercises a client did on a day (one record per client per day). Empty list clears the day. */
  setDayExercises: async (data: {
    client_id: number;
    date: string;
    exercise_ids: number[];
    details?: DayExerciseDetail[];
    notes?: string;
  }): Promise<WorkoutSession | null> => {
    const res = await api.put<WorkoutSession | null>('/sessions/day', data);
    return res.data;
  },
  deleteSession: async (id: number) => {
    const res = await api.delete(`/sessions/${id}`);
    return res.data;
  },
};

export const progressPhotoService = {
  list: async (clientId: number): Promise<ProgressPhoto[]> => {
    const res = await api.get<ProgressPhoto[]>('/progress-photos', { params: { client_id: clientId } });
    return res.data;
  },
  upload: async (data: {
    client_id: number;
    photo_date: string;
    category: PhotoPose;
    weight?: number;
    notes?: string;
    file: File;
  }): Promise<ProgressPhoto> => {
    const form = new FormData();
    form.append('client_id', String(data.client_id));
    form.append('photo_date', data.photo_date);
    form.append('category', data.category);
    if (data.weight !== undefined) form.append('weight', String(data.weight));
    if (data.notes) form.append('notes', data.notes);
    form.append('file', await prepareImageForUpload(data.file));
    const res = await api.post<ProgressPhoto>('/progress-photos', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  update: async (
    id: number,
    data: Partial<Pick<ProgressPhoto, 'photo_date' | 'category' | 'weight' | 'notes'>>,
  ): Promise<ProgressPhoto> => {
    const res = await api.patch<ProgressPhoto>(`/progress-photos/${id}`, data);
    return res.data;
  },
  remove: async (id: number) => {
    const res = await api.delete<{ message: string }>(`/progress-photos/${id}`);
    return res.data;
  },
};

export const noteService = {
  getClientNotes: async (clientId: number): Promise<TrainerNote[]> => {
    const res = await api.get<TrainerNote[]>(`/notes/client/${clientId}`);
    return res.data;
  },
  createClientNote: async (clientId: number, note: string): Promise<TrainerNote> => {
    const res = await api.post<TrainerNote>(`/notes/client/${clientId}`, { note });
    return res.data;
  },
  deleteNote: async (id: number) => {
    const res = await api.delete(`/notes/${id}`);
    return res.data;
  },
};

export const attendanceService = {
  getDailyAttendance: async (date?: string): Promise<DailyAttendanceResponse> => {
    const res = await api.get<DailyAttendanceResponse>('/attendance', { params: { attendance_date: date } });
    return res.data;
  },
  getMonthlyOverview: async (params?: {
    month?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<MonthlyAttendanceOverviewResponse> => {
    const res = await api.get<MonthlyAttendanceOverviewResponse>('/attendance/monthly-overview', { params });
    return res.data;
  },
  /** Creates the record, or updates it if one already exists for that client and date. */
  recordAttendance: async (data: { client_id: number; date: string; status: string; notes?: string }): Promise<AttendanceRecord> => {
    const res = await api.post<AttendanceRecord>('/attendance', data);
    return res.data;
  },
  getClientAttendanceHistory: async (
    clientId: number,
    params?: { date?: string; start_date?: string; end_date?: string; month?: string; status?: string }
  ): Promise<AttendanceHistorySummary> => {
    const res = await api.get<AttendanceHistorySummary>(`/attendance/client/${clientId}`, { params });
    return res.data;
  },
  deleteAttendance: async (id: number) => {
    const res = await api.delete(`/attendance/${id}`);
    return res.data;
  },
};

export const feeService = {
  getPlans: async (): Promise<MembershipPlan[]> => {
    const res = await api.get<MembershipPlan[]>('/fees/plans');
    return res.data;
  },
  createPlan: async (data: { name: string; price: string; duration_months: number; description?: string }): Promise<MembershipPlan> => {
    const res = await api.post<MembershipPlan>('/fees/plans', data);
    return res.data;
  },
  updatePlan: async (
    id: number,
    data: Partial<{ name: string; price: string; duration_months: number; description: string; is_active: boolean }>
  ): Promise<MembershipPlan> => {
    const res = await api.put<MembershipPlan>(`/fees/plans/${id}`, data);
    return res.data;
  },
  deletePlan: async (id: number) => {
    const res = await api.delete(`/fees/plans/${id}`);
    return res.data;
  },
  getMemberships: async (params?: { search?: string; has_plan?: boolean; page?: number; page_size?: number }): Promise<PaginatedMemberships> => {
    const res = await api.get<PaginatedMemberships>('/fees/memberships', { params });
    return res.data;
  },
  assignMembership: async (
    clientId: number,
    data: { plan_id: number; fee_amount?: string; billing_start_date?: string }
  ): Promise<ClientFeeAccount> => {
    const res = await api.put<ClientFeeAccount>(`/fees/clients/${clientId}/membership`, data);
    return res.data;
  },
  stopMembership: async (clientId: number): Promise<ClientFeeAccount> => {
    const res = await api.delete<ClientFeeAccount>(`/fees/clients/${clientId}/membership`);
    return res.data;
  },
  getClientAccount: async (clientId: number): Promise<ClientFeeAccount> => {
    const res = await api.get<ClientFeeAccount>(`/fees/clients/${clientId}`);
    return res.data;
  },
  getFees: async (params?: {
    month?: string;
    status?: FeeStatus;
    unpaid_only?: boolean;
    client_id?: number;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedFees> => {
    const res = await api.get<PaginatedFees>('/fees', { params });
    return res.data;
  },
  getSummary: async (month?: string): Promise<FeeSummary> => {
    const res = await api.get<FeeSummary>('/fees/summary', { params: { month } });
    return res.data;
  },
  updateFee: async (id: number, data: { amount_due?: string; due_date?: string; is_waived?: boolean; notes?: string }): Promise<FeeRecord> => {
    const res = await api.patch<FeeRecord>(`/fees/${id}`, data);
    return res.data;
  },
  recordPayment: async (
    feeId: number,
    data: { amount: string; paid_on?: string; method: PaymentMethod; reference?: string; notes?: string }
  ): Promise<FeeRecord> => {
    const res = await api.post<FeeRecord>(`/fees/${feeId}/payments`, data);
    return res.data;
  },
  deletePayment: async (paymentId: number): Promise<FeeRecord> => {
    const res = await api.delete<FeeRecord>(`/fees/payments/${paymentId}`);
    return res.data;
  },
};

export const notificationService = {
  getNotifications: async (params?: { unread_only?: boolean; type?: string; page?: number; page_size?: number }): Promise<PaginatedNotifications> => {
    const res = await api.get<PaginatedNotifications>('/notifications', { params });
    return res.data;
  },
  getUnreadCount: async (): Promise<number> => {
    const res = await api.get<{ count: number }>('/notifications/unread-count');
    return res.data.count;
  },
  markRead: async (id: number): Promise<AppNotification> => {
    const res = await api.post<AppNotification>(`/notifications/${id}/read`);
    return res.data;
  },
  markAllRead: async () => {
    const res = await api.post('/notifications/read-all');
    return res.data;
  },
};

export const getApiErrorMessage = (err: unknown, fallback = 'Something went wrong. Please try again.'): string => {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string; loc?: (string | number)[] };
    const field = first.loc ? String(first.loc[first.loc.length - 1]) : '';
    return first.msg ? `${field ? `${field}: ` : ''}${first.msg.replace(/^Value error, /, '')}` : fallback;
  }
  return fallback;
};

export const getMediaUrl = (path?: string | null): string | null => {
  if (!path) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  const token = localStorage.getItem('gym_auth_token');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const base = cleanPath.startsWith('/api/') ? cleanPath : `/api${cleanPath}`;
  if (!token) return base;
  return `${base}${base.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
};

export default api;
