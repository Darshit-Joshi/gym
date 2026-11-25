export type UserRole = 'TRAINER' | 'CLIENT';

export type ClientStatus = 'Active' | 'Inactive' | 'Pending Activation' | 'Archived';

export type FitnessGoal =
  | 'Muscle Gain'
  | 'Weight Loss'
  | 'Strength'
  | 'General Fitness'
  | 'Endurance'
  | 'Other';

export type MuscleGroup =
  | 'Chest'
  | 'Back'
  | 'Shoulders'
  | 'Biceps'
  | 'Triceps'
  | 'Legs'
  | 'Core'
  | 'Cardio'
  | 'Other';

export interface User {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
  name?: string;
  trainer_id?: number;
  client_id?: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  user_id: number;
  name: string;
  trainer_id?: number;
  client_id?: number;
}

export interface Client {
  id: number;
  user_id: number;
  trainer_id?: number;
  name: string;
  email?: string | null;
  phone?: string;
  date_of_birth?: string;
  age?: number;
  gender?: string;
  height?: number;
  current_weight?: number;
  fitness_goal?: FitnessGoal;
  status: ClientStatus;
  profile_photo?: string;
  emergency_contact?: string;
  joined_date?: string;
  training_preferences?: string;
  created_at: string;
  updated_at: string;
  /** Only on the paginated client list. */
  payment_status?: PaymentStanding;
  outstanding_amount?: number;
}

export type PaymentStanding = 'OVERDUE' | 'DUE' | 'CLEAR' | 'NO_PLAN';

export interface PaginatedClients {
  items: Client[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Exercise {
  id: number;
  name: string;
  muscle_group: MuscleGroup;
  equipment?: string;
  difficulty?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SessionExercise {
  id?: number;
  exercise_id: number;
  exercise_name?: string;
  muscle_group?: string;
  sets_completed?: number | null;
  reps?: number | null;
  weight_used?: number | null;
  notes?: string;
}

export interface WorkoutSession {
  id: number;
  client_id: number;
  client_name?: string;
  trainer_id?: number;
  workout_plan_id?: number;
  workout_name?: string;
  date: string;
  duration_minutes: number;
  notes?: string;
  status: string;
  exercises: SessionExercise[];
  created_at: string;
  updated_at: string;
}

export type PhotoPose = 'FRONT' | 'SIDE' | 'BACK' | 'OTHER';

export interface ProgressPhoto {
  id: number;
  client_id: number;
  photo_date: string;
  /** Monday of the photo's week (YYYY-MM-DD). */
  week_start: string;
  category: PhotoPose;
  weight?: number | null;
  notes?: string | null;
  /** Needs a token to load in an <img>: pass it through getMediaUrl(). */
  image_url: string;
  created_at: string;
}

export interface TrainerNote {
  id: number;
  client_id: number;
  trainer_id: number;
  trainer_name?: string;
  note: string;
  created_at: string;
  updated_at: string;
}

export interface AttendanceDashboardSummary {
  present: number;
  absent: number;
  late: number;
  unmarked: number;
}

export interface DashboardBillingSummary {
  currency: string;
  outstanding_total: number;
  overdue_total: number;
  overdue_count: number;
  collected_this_month: number;
  unread_alerts: number;
}

export type AttendanceStatusType = 'PRESENT' | 'ABSENT' | 'LATE';

export interface AttendanceRecord {
  id: number;
  client_id: number;
  client_name?: string;
  client_photo?: string;
  trainer_id: number;
  date: string;
  day_name?: string;
  formatted_date?: string;
  attendance_time?: string;
  status: AttendanceStatusType;
  notes?: string;
  recorded_by_name?: string;
  last_modified_by_name?: string;
  last_modified_time?: string;
  created_at: string;
  updated_at: string;
}

export interface DailyAttendanceClientItem {
  client_id: number;
  client_name: string;
  client_photo?: string;
  status?: AttendanceStatusType | null;
  notes?: string;
  attendance_id?: number;
  membership_status: string;
  attendance_time?: string;
  day_name?: string;
  formatted_date?: string;
  recorded_by_name?: string;
  last_modified_by_name?: string;
  last_modified_time?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DailyAttendanceResponse {
  date: string;
  day_name?: string;
  formatted_date?: string;
  present_count: number;
  absent_count: number;
  late_count: number;
  unmarked_count: number;
  total_clients: number;
  clients: DailyAttendanceClientItem[];
}

export interface AttendanceHistorySummary {
  total_recorded: number;
  present_count: number;
  absent_count: number;
  late_count: number;
  attendance_percentage: number;
  records: AttendanceRecord[];
}

export interface MonthlyClientOverviewItem {
  client_id: number;
  client_name: string;
  client_photo?: string | null;
  membership_status: string;
  present_count: number;
  absent_count: number;
  late_count: number;
  total_recorded: number;
  attendance_percentage: number;
}

export interface MonthlyAttendanceOverviewResponse {
  month: string;
  month_name: string;
  total_clients: number;
  page: number;
  page_size: number;
  total_pages: number;
  clients: MonthlyClientOverviewItem[];
}

// ---------------------------------------------------------------------------
// Fees & billing
// ---------------------------------------------------------------------------

export type FeeStatus = 'PAID' | 'WAIVED' | 'OVERDUE' | 'PARTIAL' | 'PENDING' | 'UPCOMING';
export type PaymentMethod = 'CASH' | 'UPI' | 'CARD' | 'BANK_TRANSFER' | 'OTHER';

export interface MembershipPlan {
  id: number;
  name: string;
  price: number;
  duration_months: number;
  description?: string | null;
  is_active: boolean;
  client_count: number;
  created_at: string;
}

export interface FeePayment {
  id: number;
  fee_id: number;
  amount: number;
  paid_on: string;
  method: PaymentMethod;
  reference?: string | null;
  notes?: string | null;
  recorded_by?: string | null;
  created_at: string;
}

export interface FeeRecord {
  id: number;
  client_id: number;
  client_name?: string | null;
  client_phone?: string | null;
  plan_name?: string | null;
  period_start: string;
  period_end: string;
  due_date: string;
  amount_due: number;
  amount_paid: number;
  balance: number;
  status: FeeStatus;
  is_waived: boolean;
  notes?: string | null;
  days_overdue: number;
  payments: FeePayment[];
  reminder_whatsapp_link?: string | null;
}

export interface PaginatedFees {
  items: FeeRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  currency: string;
}

export interface ClientMembershipInfo {
  client_id: number;
  client_name: string;
  client_phone?: string | null;
  client_status: string;
  plan_id?: number | null;
  plan_name?: string | null;
  duration_months?: number | null;
  fee_amount?: number | null;
  billing_start_date?: string | null;
  next_due_date?: string | null;
  outstanding_amount: number;
  overdue_count: number;
}

export interface PaginatedMemberships {
  items: ClientMembershipInfo[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  currency: string;
}

export interface ClientFeeAccount {
  membership: ClientMembershipInfo;
  fees: FeeRecord[];
  total_paid: number;
  currency: string;
}

export interface FeeSummary {
  month: string;
  month_name: string;
  currency: string;
  billed_amount: number;
  collected_amount: number;
  collected_for_month_dues: number;
  collection_rate: number;
  fees_due_count: number;
  paid_count: number;
  unpaid_count: number;
  outstanding_total: number;
  overdue_total: number;
  overdue_count: number;
  clients_without_plan: number;
}

// ---------------------------------------------------------------------------
// Notifications & settings
// ---------------------------------------------------------------------------

export type NotificationType = 'ABSENCE_STREAK' | 'ABSENCE_MONTHLY' | 'FEE_DUE_SOON' | 'FEE_OVERDUE' | 'STORAGE_LOW';
export type NotificationSeverity = 'INFO' | 'WARNING' | 'CRITICAL';

export interface AppNotification {
  id: number;
  type: NotificationType;
  severity: NotificationSeverity;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
  client_id?: number | null;
  client_name?: string | null;
  fee_id?: number | null;
  link?: string | null;
  whatsapp_link?: string | null;
}

export interface PaginatedNotifications {
  items: AppNotification[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UpcomingDue {
  fee_id: number;
  client_id: number;
  client_name: string;
  due_date: string;
  balance: number;
  status: FeeStatus;
}

export interface AttendanceTrendDay {
  date: string;
  checked_in: number;
  absent: number;
}

export type ActivityKind = 'ATTENDANCE' | 'PAYMENT' | 'WORKOUT' | 'CLIENT_ADDED';

export interface ActivityItem {
  kind: ActivityKind;
  client_id: number;
  client_name: string;
  client_photo?: string | null;
  date: string;
  at: string;
  detail: string;
}

export interface TrainerDashboardData {
  total_clients: number;
  active_clients: number;
  today_attendance: AttendanceDashboardSummary;
  billing: DashboardBillingSummary;
  upcoming_dues: UpcomingDue[];
  recent_clients: Client[];
  attendance_trend: AttendanceTrendDay[];
  recent_activity: ActivityItem[];
}

export interface DayExerciseDetail {
  exercise_id: number;
  sets_completed?: number | null;
  reps?: number | null;
  weight_used?: number | null;
}
