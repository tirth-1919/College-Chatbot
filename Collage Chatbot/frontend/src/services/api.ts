import {
  User, ChatMessage, FeeRecord, FacultyMember, TimetableEntry, ExamEntry,
  FacilityData, EventData, KnowledgeConflict, MLModelItem, DashboardMetrics,
  PendingKnowledgeItem, TrainingExampleItem
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

  async enhancedRegister(data: {
    full_name: string;
    email: string;
    password: string;
    confirm_password: string;
    role?: string;
    enrollment_number?: string;
    course_code?: string;
    semester?: number;
  }): Promise<{ access_token: string; user: User }> {
    const res = await fetch(`${API_BASE}/auth/register/enhanced`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Registration failed');
    const responseData = await res.json();
    setAuthToken(responseData.access_token);
    return responseData;
  },

  async forgotPassword(email: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    return await res.json();
  },

  async resetPassword(token: string, newPassword: string, confirmPassword: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token, new_password: newPassword, confirm_password: confirmPassword }),
    });
    return await res.json();
  },

  async getGoogleAuthUrl(redirectUri?: string): Promise<{ auth_url: string; state: string }> {
    const params = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : '';
    const res = await fetch(`${API_BASE}/auth/google/auth-url${params}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) throw new Error('Failed to get Google auth URL');
    return await res.json();
  },

  async handleGoogleCallback(code: string, state: string): Promise<{ access_token: string; user: User }> {
    const res = await fetch(`${API_BASE}/auth/google/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, state }),
    });
    if (!res.ok) throw new Error('Google authentication failed');
    const data = await res.json();
    setAuthToken(data.access_token);
    return data;
  },

  // Chat & Voice
  async sendMessage(message: string, conversationId?: string, mode: 'TEXT' | 'VOICE' = 'TEXT'): Promise<ChatMessage> {
    try {
      const res = await fetch(`${API_BASE}/chat/send`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ message, conversation_id: conversationId, mode }),
      });

      if (!res.ok) {
        let errMessage = "Sorry, I couldn't get an answer right now. Please try again.";
        try {
          const errData = await res.json();
          if (errData && (errData.detail || errData.error || errData.message)) {
            errMessage = errData.detail || errData.error || errData.message;
          }
        } catch {}

        if (res.status === 401) {
          errMessage = 'Authentication required. Please sign in to access this information.';
        } else if (res.status === 403) {
          errMessage = 'Access restricted. You do not have permission to view this resource.';
        } else if (res.status === 404) {
          errMessage = "I couldn't find verified AIT information about that.";
        } else if (res.status === 429) {
          errMessage = 'Too many requests. Please wait a moment and try again.';
        } else if (res.status >= 500) {
          errMessage = 'Sorry, the server encountered an error. Please try again in a moment.';
        }

        throw new Error(errMessage);
      }

      const data = await res.json();
      const content = data.content || data.answer || '';
      if (!content.trim()) {
        throw new Error("Assistant returned an empty answer");
      }
      return {
        id: data.id || data.message_id || `asst-${Date.now()}`,
        role: 'assistant',
        content: content,
        answer: content,
        status: 'complete',
        conversation_id: data.conversation_id,
        message_id: data.message_id || data.id,
        language: data.language,
        intent: data.intent,
        entities: data.entities || {},
        selected_source: data.selected_source,
        confidence: data.confidence,
        sources: data.sources || [],
        images: data.images || [],
        suggested_followups: data.suggested_followups || [],
        voice_asset_id: data.voice_asset_id,
        is_general_knowledge: data.is_general_knowledge,
        timestamp: data.timestamp || new Date().toISOString(),
      };
    } catch (err: any) {
      if (err.name === 'TypeError' || err.message?.includes('fetch') || err.message?.includes('NetworkError')) {
        throw new Error('Network connection failed. Please check your connection and try again.');
      }
      throw err;
    }
  },

  async sendVoiceTranscript(transcript: string, conversationId?: string): Promise<{ chat_response: ChatMessage }> {
    const formData = new FormData();
    formData.append('transcript', transcript);
    if (conversationId) formData.append('conversation_id', conversationId);

    const headers: Record<string, string> = {};
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

    try {
      const res = await fetch(`${API_BASE}/chat/voice`, {
        method: 'POST',
        headers,
        body: formData,
      });
      if (!res.ok) throw new Error('Voice query failed');
      const data = await res.json();
      const rawRes = data.chat_response || {};
      const content = rawRes.content || rawRes.answer || '';
      const normalizedResponse: ChatMessage = {
        id: rawRes.id || rawRes.message_id || `asst-${Date.now()}`,
        role: 'assistant',
        content: content,
        answer: content,
        status: 'complete',
        conversation_id: rawRes.conversation_id,
        message_id: rawRes.message_id || rawRes.id,
        language: rawRes.language || data.language,
        intent: rawRes.intent,
        entities: rawRes.entities || {},
        selected_source: rawRes.selected_source,
        confidence: rawRes.confidence,
        sources: rawRes.sources || [],
        images: rawRes.images || [],
        suggested_followups: rawRes.suggested_followups || [],
        voice_asset_id: rawRes.voice_asset_id,
        is_general_knowledge: rawRes.is_general_knowledge,
        timestamp: rawRes.timestamp || new Date().toISOString(),
      };
      return {
        chat_response: normalizedResponse,
      };
    } catch (err: any) {
      if (err.name === 'TypeError' || err.message?.includes('fetch')) {
        throw new Error('Network connection failed. Please check your connection.');
      }
      throw err;
    }
  },

  async submitFeedback(messageId: string, feedback: 'helpful' | 'unhelpful' | 'reported'): Promise<void> {
    await fetch(`${API_BASE}/chat/feedback`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ message_id: messageId, feedback }),
    });
  },

  async getConversations(search?: string): Promise<any[]> {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    const res = await fetch(`${API_BASE}/chat/conversations${params}`, { headers: getHeaders() });
    if (!res.ok) return [];
    return await res.json();
  },

  async getConversation(conversationId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/chat/conversations/${conversationId}`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to get conversation');
    return await res.json();
  },

  async renameConversation(conversationId: string, title: string): Promise<any> {
    const res = await fetch(`${API_BASE}/chat/conversations/${conversationId}/rename`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error('Failed to rename conversation');
    return await res.json();
  },

  async deleteConversation(conversationId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/chat/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete conversation');
    return await res.json();
  },

  async archiveConversation(conversationId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/chat/conversations/${conversationId}/archive`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to archive conversation');
    return await res.json();
  },

  async pinConversation(conversationId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/chat/conversations/${conversationId}/pin`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to pin conversation');
    return await res.json();
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

  async getAdvancedAnalytics(): Promise<any> {
    const res = await fetch(`${API_BASE}/admin/analytics`, { headers: getHeaders() });
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
  },

  // Knowledge Sync & Review
  async getPendingKnowledge(status?: string): Promise<PendingKnowledgeItem[]> {
    const url = status ? `${API_BASE}/admin/knowledge/pending?status=${status}` : `${API_BASE}/admin/knowledge/pending`;
    const res = await fetch(url, { headers: getHeaders() });
    return await res.json();
  },

  async approveKnowledgeUpdate(updateId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/admin/knowledge/${updateId}/approve`, {
      method: 'POST',
      headers: getHeaders(),
    });
    return await res.json();
  },

  async rejectKnowledgeUpdate(updateId: string, reason?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/admin/knowledge/${updateId}/reject`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ reason }),
    });
    return await res.json();
  },

  async archiveKnowledgeSource(sourceId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/admin/knowledge/${sourceId}/archive`, {
      method: 'POST',
      headers: getHeaders(),
    });
    return await res.json();
  },

  async reindexRAG(): Promise<any> {
    const res = await fetch(`${API_BASE}/admin/rag/reindex`, {
      method: 'POST',
      headers: getHeaders(),
    });
    return await res.json();
  },

  // Intent Training
  async getTrainingExamples(status?: string): Promise<TrainingExampleItem[]> {
    const url = status ? `${API_BASE}/admin/training/examples?status=${status}` : `${API_BASE}/admin/training/examples`;
    const res = await fetch(url, { headers: getHeaders() });
    return await res.json();
  },

  async approveTrainingExample(exampleId: string, approvedIntent: string): Promise<any> {
    const res = await fetch(`${API_BASE}/admin/training/${exampleId}/approve`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ approved_intent: approvedIntent }),
    });
    return await res.json();
  },

  async rejectTrainingExample(exampleId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/admin/training/${exampleId}/reject`, {
      method: 'POST',
      headers: getHeaders(),
    });
    return await res.json();
  },

  async retrainIntentModel(minAccuracy = 0.85, minF1 = 0.85): Promise<any> {
    const res = await fetch(`${API_BASE}/admin/training/retrain?min_accuracy=${minAccuracy}&min_f1=${minF1}`, {
      method: 'POST',
      headers: getHeaders(),
    });
    return await res.json();
  },


  async generateStudyPlan(data: {
    course_code: string;
    semester: number;
    available_hours_per_day: number;
    language?: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/academic/study-plan/generate`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to generate study plan');
    return await res.json();
  },

  async reopenConflict(conflictId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/knowledge/conflicts/reopen?conflict_id=${conflictId}`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to reopen conflict');
    return await res.json();
  },

  async reauthenticate(password: string, actionType: string = 'DESTRUCTIVE_ACTION'): Promise<{ reauth_token: string }> {
    const res = await fetch(`${API_BASE}/auth/reauth`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ password, action_type: actionType }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Re-authentication failed');
    return await res.json();
  },

  async deleteKnowledgeSource(sourceId: string, reauthToken?: string): Promise<any> {
    const headers = getHeaders();
    const url = reauthToken
      ? `${API_BASE}/admin/knowledge/source/${sourceId}?reauth_token=${encodeURIComponent(reauthToken)}`
      : `${API_BASE}/admin/knowledge/source/${sourceId}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers,
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to delete knowledge source');
    return await res.json();
  }
};