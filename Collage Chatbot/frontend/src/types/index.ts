export type UserRole = 'PUBLIC' | 'STUDENT' | 'FACULTY' | 'ADMIN' | 'SUPER_ADMIN';

export interface User {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  enrollment_number?: string;
  current_semester?: number;
}

export interface SourceCard {
  source_type: 'ADMIN_VERIFIED_DATABASE' | 'OFFICIAL_AIT_WEBSITE' | 'OFFICIAL_DOCUMENT' | 'GENERAL_AI';
  title: string;
  source_url?: string;
  page_or_record?: string;
  authority_level: string;
  verified_at?: string;
}

export interface ImageCard {
  image_url: string;
  source_url: string;
  source_page: string;
  caption?: string;
  alt_text?: string;
  year?: number;
  category?: string;
  provenance?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  answer?: string;
  status?: 'thinking' | 'complete' | 'error';
  conversation_id?: string;
  message_id?: string;
  language?: string;
  intent?: string;
  entities?: Record<string, any>;
  selected_source?: string;
  confidence?: number;
  sources?: SourceCard[];
  images?: ImageCard[];
  suggested_followups?: string[];
  voice_asset_id?: string;
  is_general_knowledge?: boolean;
  feedback?: string;
  timestamp: string;
}

export interface FeeRecord {
  id: string;
  course_code: string;
  course_name: string;
  academic_year: string;
  tuition_fee: number;
  exam_fee: number;
  other_charges: number;
  total_fee: number;
  payment_terms: string;
  verification_status: string;
  version: number;
}

export interface FacultyMember {
  id: string;
  employee_id: string;
  name: string;
  designation: string;
  department: string;
  email?: string;
  office_room?: string;
  office_hours?: string;
  qualification?: string;
  subjects_taught: string[];
}

export interface TimetableEntry {
  id: string;
  day: string;
  start_time: string;
  end_time: string;
  subject: string;
  faculty: string;
  room: string;
  division: string;
}

export interface ExamEntry {
  id: string;
  subject_code: string;
  subject_name: string;
  exam_type: string;
  date: string;
  start_time: string;
  end_time: string;
  room: string;
  status: string;
}

export interface FacilityData {
  id: string;
  name: string;
  category: string;
  location?: string;
  description?: string;
  timings?: string;
  images: ImageCard[];
}

export interface EventData {
  id: string;
  name: string;
  event_type: string;
  date_start: string;
  date_end?: string;
  calendar_year: number;
  academic_year: string;
  description: string;
  organizer: string;
  official_source_url: string;
  images: ImageCard[];
}

export interface KnowledgeConflict {
  id: string;
  topic: string;
  source_a_type: string;
  source_a_value: string;
  source_a_ref?: string;
  source_b_type: string;
  source_b_value: string;
  source_b_ref?: string;
  status: string;
  resolution_choice?: string;
  created_at: string;
}

export interface MLModelItem {
  id: string;
  name: string;
  task: string;
  version: string;
  model_type: string;
  accuracy: number;
  f1_score: number;
  is_active: boolean;
  created_at: string;
}

export interface DashboardMetrics {
  total_users: number;
  total_conversations: number;
  total_messages: number;
  active_conflicts: number;
  knowledge_sources: number;
  total_events: number;
  total_facilities: number;
  open_tickets: number;
  ai_accuracy_rate: number;
  groundedness_score: number;
  active_ml_model: string;
  system_status: string;
}

export interface PendingKnowledgeItem {
  id: string;
  source_id?: string;
  source_url: string;
  title: string;
  category: string;
  source_type: string;
  old_value?: string;
  new_value: string;
  change_type: string;
  change_summary?: string;
  content_hash: string;
  approval_status: string;
  detected_at: string;
  reviewed_at?: string;
  reviewed_by?: string;
  rejection_reason?: string;
  metadata?: Record<string, any>;
}

export interface TrainingExampleItem {
  id: string;
  text: string;
  language: string;
  predicted_intent?: string;
  approved_intent?: string;
  status: string;
  source: string;
  confidence: number;
  created_at: string;
  approved_at?: string;
  approved_by?: string;
  metadata?: Record<string, any>;
}

