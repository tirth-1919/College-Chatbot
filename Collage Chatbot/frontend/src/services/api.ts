import {
  User, ChatMessage, FeeRecord, FacultyMember, TimetableEntry, ExamEntry,
  FacilityData, EventData, KnowledgeConflict, MLModelItem, DashboardMetrics
} from '../types';

const API_BASE = '/api/v1';

let authToken: string | null = localStorage.getItem('ait_token');

export const setAuthToken = (token: string | null) => {
  authToken = token;
  if (token) {
    localStorage.setItem('ait_token', token);
  } else {
    localStorage.removeItem('ait_token');
  }
};

const getHeaders = () => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
};

export const api = {
  // Auth
  async login(email: string, password: string):Promise<{ access_token: string; user: User }> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Login failed');
    const data = await res.json();
    setAuthToken(data.access_token);
    return data;
  },

  async getCurrentUser(): Promise<User | null> {
    if (!authToken) return null;
    try {
      const res = await fetch(`${API_BASE}/auth/me`, { headers: getHeaders() });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  // Chat & Voice
  async sendMessage(message: string, conversationId?: string, mode: 'TEXT' | 'VOICE' = 'TEXT'): Promise<ChatMessage> {
    const res = await fetch(`${API_BASE}/chat/send`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ message, conversation_id: conversationId, mode }),
    });
    if (!res.ok) throw new Error('Failed to send message');
    return await res.json();
  },

  async sendVoiceTranscript(transcript: string, conversationId?: string): Promise<{ chat_response: ChatMessage }> {
    const formData = new FormData();
    formData.append('transcript', transcript);
    if (conversationId) formData.append('conversation_id', conversationId);

    const headers: Record<string, string> = {};
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

    const res = await fetch(`${API_BASE}/chat/voice`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) throw new Error('Voice query failed');
    return await res.json();
  },

  async submitFeedback(messageId: string, feedback: 'helpful' | 'unhelpful' | 'reported'): Promise<void> {
    await fetch(`${API_BASE}/chat/feedback`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ message_id: messageId, feedback }),
    });
  },

  getVoiceAudioUrl(assetId: string): string {
    return `${API_BASE}/chat/voice-asset/${assetId}`;
  },

  // Academic Master Data
  async getFees(courseCode?: string, academicYear?: string): Promise<FeeRecord[]> {
    const params = new URLSearchParams();
    if (courseCode) params.append('course_code', courseCode);
    if (academicYear) params.append('academic_year', academicYear);
    const res = await fetch(`${API_BASE}/academic/fees?${params.toString()}`, { headers: getHeaders() });
    return await res.json();
  },

  async updateFee(feeData: {
    course_code: string;
    academic_year: string;
    tuition_fee: number;
    exam_fee?: number;
    other_charges?: number;
    payment_terms?: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/academic/fees`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(feeData),
    });
    if (!res.ok) throw new Error('Failed to update fee record');
    return await res.json();
  },

  async getFaculty(): Promise<FacultyMember[]> {
    const res = await fetch(`${API_BASE}/academic/faculty`, { headers: getHeaders() });
    return await res.json();
  },

  async getTimetable(courseCode = 'BCA', semester = 4, day?: string): Promise<TimetableEntry[]> {
    const params = new URLSearchParams({ course_code: courseCode, semester: semester.toString() });
    if (day) params.append('day', day);
    const res = await fetch(`${API_BASE}/academic/timetable?${params.toString()}`, { headers: getHeaders() });
    return await res.json();
  },

  async getExams(courseCode = 'BCA', semester = 4): Promise<ExamEntry[]> {
    const res = await fetch(`${API_BASE}/academic/exams?course_code=${courseCode}&semester=${semester}`, { headers: getHeaders() });
    return await res.json();
  },

  // Visual & Facilities
  async getFacilities(): Promise<FacilityData[]> {
    const res = await fetch(`${API_BASE}/visual/facilities`, { headers: getHeaders() });
    return await res.json();
  },

  async getEvents(year?: number): Promise<EventData[]> {
    const url = year ? `${API_BASE}/visual/events?year=${year}` : `${API_BASE}/visual/events`;
    const res = await fetch(url, { headers: getHeaders() });
    return await res.json();
  },

  // Knowledge & Conflicts
  async getConflicts(): Promise<KnowledgeConflict[]> {
    const res = await fetch(`${API_BASE}/knowledge/conflicts`, { headers: getHeaders() });
    return await res.json();
  },

  async resolveConflict(conflictId: string, resolutionChoice: string, customValue?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/knowledge/conflicts/resolve`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ conflict_id: conflictId, resolution_choice: resolutionChoice, custom_value: customValue }),
    });
    return await res.json();
  },

  async syncWebsite(): Promise<any> {
    const res = await fetch(`${API_BASE}/knowledge/sync/website`, {
      method: 'POST',
      headers: getHeaders(),
    });
    return await res.json();
  },

  // Admin & ML
  async getMetrics(): Promise<DashboardMetrics> {
    const res = await fetch(`${API_BASE}/admin/metrics`, { headers: getHeaders() });
    return await res.json();
  },

  async getMLModels(): Promise<MLModelItem[]> {
    const res = await fetch(`${API_BASE}/admin/ml/models`, { headers: getHeaders() });
    return await res.json();
  },

  async rollbackModel(task: string, version: string): Promise<any> {
    const res = await fetch(`${API_BASE}/admin/ml/rollback?task=${task}&version=${version}`, {
      method: 'POST',
      headers: getHeaders(),
    });
    return await res.json();
  }
};
