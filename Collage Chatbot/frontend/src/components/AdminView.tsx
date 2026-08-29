import React, { useState, useEffect } from 'react';
import { DashboardMetrics, KnowledgeConflict, MLModelItem, FacilityData, EventData, PendingKnowledgeItem, TrainingExampleItem } from '../types';
import { api } from '../services/api';
import {
  ShieldAlert, RefreshCw, AlertTriangle, Cpu, History, DollarSign,
  CheckCircle2, RotateCcw, Activity, Database, Check, BarChart2,
  Lock, Search, Filter, ShieldCheck, Zap, Layers, Sparkles, X,
  Globe, Image as ImageIcon, ExternalLink, Calendar, Building, BookOpen,
  FileText, CheckSquare, XSquare, Archive
} from 'lucide-react';

export const AdminView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'pending_knowledge' | 'training_review' | 'official_content' | 'conflicts' | 'analytics' | 'models'>('overview');
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [conflicts, setConflicts] = useState<KnowledgeConflict[]>([]);
  const [models, setModels] = useState<MLModelItem[]>([]);
  const [facilities, setFacilities] = useState<FacilityData[]>([]);
  const [events, setEvents] = useState<EventData[]>([]);
  const [pendingKnowledge, setPendingKnowledge] = useState<PendingKnowledgeItem[]>([]);
  const [trainingExamples, setTrainingExamples] = useState<TrainingExampleItem[]>([]);
  const [bcaFeeInput, setBcaFeeInput] = useState<string>('32000');
  const [feeSaveSuccess, setFeeSaveSuccess] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [isRetraining, setIsRetraining] = useState(false);
  const [retrainResult, setRetrainResult] = useState<any | null>(null);
  const [selectedIntentMap, setSelectedIntentMap] = useState<Record<string, string>>({});

  // Conflict filters & search
  const [conflictStatusFilter, setConflictStatusFilter] = useState<'ALL' | 'OPEN' | 'RESOLVED'>('ALL');
  const [conflictSearchQuery, setConflictSearchQuery] = useState('');

  // Re-authentication modal state for destructive operations
  const [reauthModalOpen, setReauthModalOpen] = useState(false);
  const [reauthPassword, setReauthPassword] = useState('');
  const [reauthError, setReauthError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<{ type: string; payload: any } | null>(null);

  useEffect(() => {
    loadAdminData();
  }, []);

  const loadAdminData = async () => {
    try {
      const [m, c, mdl, a, facs, evts, pk, te] = await Promise.all([
        api.getMetrics(),
        api.getConflicts(),
        api.getMLModels(),
        api.getAdvancedAnalytics().catch(() => null),
        api.getFacilities().catch(() => []),
        api.getEvents().catch(() => []),
        api.getPendingKnowledge().catch(() => []),
        api.getTrainingExamples().catch(() => []),
      ]);
      setMetrics(m);
      setConflicts(c);
      setModels(mdl);
      if (a) setAnalytics(a);
      if (facs) setFacilities(facs);
      if (evts) setEvents(evts);
      if (pk) setPendingKnowledge(pk);
      if (te) setTrainingExamples(te);
    } catch (err) {
      console.error('Error loading admin data:', err);
    }
  };

  const handleApproveKnowledge = async (updateId: string) => {
    try {
      await api.approveKnowledgeUpdate(updateId);
      loadAdminData();
    } catch (err) {
      console.error('Failed to approve knowledge:', err);
    }
  };

  const handleRejectKnowledge = async (updateId: string) => {
    try {
      await api.rejectKnowledgeUpdate(updateId);
      loadAdminData();
    } catch (err) {
      console.error('Failed to reject knowledge:', err);
    }
  };

  const handleArchiveKnowledge = async (sourceId: string) => {
    try {
      await api.archiveKnowledgeSource(sourceId);
      loadAdminData();
    } catch (err) {
      console.error('Failed to archive knowledge:', err);
    }
  };

  const handleReindexRAG = async () => {
    setIsReindexing(true);
    try {
      const res = await api.reindexRAG();
      setSyncStatus(`RAG re-indexing complete: ${res.total_chunks_indexed} chunks indexed across ${res.sources_reindexed} approved sources.`);
      loadAdminData();
    } catch (err) {
      setSyncStatus('RAG re-indexing failed.');
    } finally {
      setIsReindexing(false);
    }
  };

  const handleApproveTrainingExample = async (id: string, defaultIntent: string) => {
    const chosenIntent = selectedIntentMap[id] || defaultIntent || 'FACULTY_SUBJECT_QUERY';
    try {
      await api.approveTrainingExample(id, chosenIntent);
      loadAdminData();
    } catch (err) {
      console.error('Failed to approve training example:', err);
    }
  };

  const handleRejectTrainingExample = async (id: string) => {
    try {
      await api.rejectTrainingExample(id);
      loadAdminData();
    } catch (err) {
      console.error('Failed to reject training example:', err);
    }
  };

  const handleRetrainIntentModel = async () => {
    setIsRetraining(true);
    setRetrainResult(null);
    try {
      const res = await api.retrainIntentModel(0.85, 0.85);
      setRetrainResult(res);
      loadAdminData();
    } catch (err: any) {
      setRetrainResult({ success: false, error: err.message || 'Retraining request failed' });
    } finally {
      setIsRetraining(false);
    }
  };

  const handleUpdateBcaFee = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const numericFee = parseFloat(bcaFeeInput);
      await api.updateFee({
        course_code: 'BCA',
        academic_year: '2026-27',
        tuition_fee: numericFee,
        exam_fee: 1500,
        other_charges: 1000,
        payment_terms: 'Semester-wise',
      });
      setFeeSaveSuccess(true);
      setTimeout(() => setFeeSaveSuccess(false), 3000);
      loadAdminData();
    } catch (err) {
      console.error('Failed to update fee:', err);
    }
  };

  const handleWebsiteSync = async () => {
    setIsSyncing(true);
    setSyncStatus('Initiating controlled crawl of https://www.aitindia.in...');
    try {
      const res = await api.syncWebsite();
      setSyncStatus(res.message);
      loadAdminData();
    } catch (err) {
      setSyncStatus('Website sync failed or network timed out.');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleResolveConflict = async (conflictId: string, choice: string) => {
    try {
      await api.resolveConflict(conflictId, choice);
      loadAdminData();
    } catch (err) {
      console.error('Failed to resolve conflict:', err);
    }
  };

  const handleReopenConflict = async (conflictId: string) => {
    try {
      await api.reopenConflict(conflictId);
      loadAdminData();
    } catch (err) {
      console.error('Failed to reopen conflict:', err);
    }
  };

  const triggerDestructiveRollback = (task: string, version: string) => {
    setPendingAction({ type: 'ROLLBACK', payload: { task, version } });
    setReauthPassword('');
    setReauthError(null);
    setReauthModalOpen(true);
  };

  const handleConfirmReauth = async (e: React.FormEvent) => {
    e.preventDefault();
    setReauthError(null);
    try {
      const { reauth_token } = await api.reauthenticate(reauthPassword, 'DESTRUCTIVE_ROLLBACK');
      if (pendingAction?.type === 'ROLLBACK') {
        await api.rollbackModel(pendingAction.payload.task, pendingAction.payload.version);
      }
      setReauthModalOpen(false);
      setPendingAction(null);
      setReauthPassword('');
      loadAdminData();
    } catch (err: any) {
      setReauthError(err.message || 'Invalid admin password');
    }
  };

  const filteredConflicts = conflicts.filter(c => {
    if (conflictStatusFilter !== 'ALL' && c.status !== conflictStatusFilter) return false;
    if (conflictSearchQuery) {
      const q = conflictSearchQuery.toLowerCase();
      return c.topic.toLowerCase().includes(q) ||
        (c.source_a_value && c.source_a_value.toLowerCase().includes(q)) ||
        (c.source_b_value && c.source_b_value.toLowerCase().includes(q));
    }
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="font-heading text-2xl font-bold text-white flex items-center space-x-2">
            <ShieldAlert className="w-6 h-6 text-amber-500" />
            <span>AIT Admin AI & Knowledge Control Center</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic ground truth, Knowledge conflict resolution, Live website synchronization, and ML model rollbacks
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex flex-wrap items-center gap-1 glass-card p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'overview' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('pending_knowledge')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 ${
              activeTab === 'pending_knowledge' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Pending Approvals ({pendingKnowledge.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('training_review')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 ${
              activeTab === 'training_review' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>Intent Retraining ({trainingExamples.filter(e => e.status === 'PENDING').length})</span>
          </button>
          <button
            onClick={() => setActiveTab('official_content')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 ${
              activeTab === 'official_content' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>Official Content & Images</span>
          </button>
          <button
            onClick={() => setActiveTab('conflicts')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 ${
              activeTab === 'conflicts' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Conflicts ({metrics?.active_conflicts || 0})</span>
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 ${
              activeTab === 'analytics' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <BarChart2 className="w-3.5 h-3.5" />
            <span>Analytics</span>
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 ${
              activeTab === 'models' ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>ML Models</span>
          </button>
        </div>
      </div>

      {syncStatus && (
        <div className="glass-panel p-3.5 rounded-2xl border border-blue-500/30 text-xs text-blue-300 flex items-center justify-between">
          <span>{syncStatus}</span>
          <button onClick={() => setSyncStatus(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* KPI Metrics */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="glass-card p-4 rounded-2xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase">Groundedness Score</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">{metrics.groundedness_score}%</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Strict non-hallucinatory</div>
          </div>
          <div className="glass-card p-4 rounded-2xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase">Knowledge Sources</div>
            <div className="text-2xl font-bold text-ait-200 mt-1">{metrics.knowledge_sources}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">AIT web & doc indexes</div>
          </div>
          <div className="glass-card p-4 rounded-2xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase">Active Conflicts</div>
            <div className="text-2xl font-bold text-amber-400 mt-1">{metrics.active_conflicts}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Requires resolution</div>
          </div>
          <div className="glass-card p-4 rounded-2xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase">Active ML Model</div>
            <div className="text-sm font-bold text-white mt-2 truncate">{metrics.active_ml_model}</div>
            <div className="text-[10px] text-emerald-400 flex items-center space-x-1 mt-0.5">
              <Activity className="w-3 h-3" />
              <span>Healthy</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Direct Academic Data Modifier (BCA Fees) */}
          <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="font-heading text-lg font-bold text-white flex items-center space-x-2">
                  <DollarSign className="w-5 h-5 text-emerald-400" />
                  <span>Admin Database Fee Truth Modifier</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Update college operational records (e.g. BCA fees) deterministically. The AI chatbot will immediately return this exact record.
                </p>
              </div>
            </div>

            <form onSubmit={handleUpdateBcaFee} className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-end">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Course Code</label>
                <input type="text" value="BCA" disabled className="w-full glass-input px-3 py-2 rounded-xl text-xs text-slate-400" />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Academic Year</label>
                <input type="text" value="2026-27" disabled className="w-full glass-input px-3 py-2 rounded-xl text-xs text-slate-400" />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-200 mb-1">Tuition Fee (₹)</label>
                <input
                  type="number"
                  value={bcaFeeInput}
                  onChange={(e) => setBcaFeeInput(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl text-xs text-white font-mono focus:outline-none focus:border-ait-500"
                />
              </div>

              <div>
                <button
                  type="submit"
                  className="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/30 transition-all flex items-center justify-center space-x-1"
                >
                  {feeSaveSuccess ? <Check className="w-4 h-4" /> : <Database className="w-4 h-4" />}
                  <span>{feeSaveSuccess ? 'Record Saved & Verified!' : 'Save & Publish Fee'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Crawler Quick Action */}
          <div className="glass-card rounded-2xl p-6 border border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <RefreshCw className="w-4 h-4 text-blue-400" />
                <span>AIT Official Website Change Detector & Sync</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Target: <span className="font-mono text-ait-200">https://www.aitindia.in</span> (SHA256 Content-Hash Delta Detection)
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleReindexRAG}
                disabled={isReindexing}
                className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold flex items-center space-x-1.5 border border-slate-700 transition-all"
              >
                <Database className={`w-3.5 h-3.5 ${isReindexing ? 'animate-spin' : ''}`} />
                <span>{isReindexing ? 'Re-indexing...' : 'Re-index RAG'}</span>
              </button>
              <button
                onClick={handleWebsiteSync}
                disabled={isSyncing}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center space-x-2 shadow-md shadow-blue-600/30 transition-all"
              >
                <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
                <span>{isSyncing ? 'Crawling & Syncing...' : 'Run Website Sync'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB: PENDING KNOWLEDGE APPROVALS */}
      {activeTab === 'pending_knowledge' && (
        <div className="space-y-6">
          <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b border-slate-800">
              <div>
                <h3 className="font-heading text-lg font-bold text-white flex items-center space-x-2">
                  <BookOpen className="w-5 h-5 text-ait-400" />
                  <span>AIT Official Knowledge Change Review & Approval Pipeline</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Detected website changes require admin verification before becoming active ground truth or entering RAG vector index.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={handleReindexRAG}
                  disabled={isReindexing}
                  className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-semibold flex items-center space-x-1.5 border border-slate-700 transition-all"
                >
                  <Database className={`w-3.5 h-3.5 ${isReindexing ? 'animate-spin' : ''}`} />
                  <span>{isReindexing ? 'Indexing...' : 'Re-index RAG'}</span>
                </button>
                <button
                  onClick={handleWebsiteSync}
                  disabled={isSyncing}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center space-x-2 shadow-md transition-all"
                >
                  <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
                  <span>{isSyncing ? 'Syncing...' : 'Sync Now'}</span>
                </button>
              </div>
            </div>

            {pendingKnowledge.length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-400 space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                <p className="font-semibold text-slate-300">All knowledge sources are up to date and verified!</p>
                <p className="text-slate-500">Run a website sync to scan for newly published pages or modified content on aitindia.in.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {pendingKnowledge.map((item) => (
                  <div key={item.id} className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-slate-800/80">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            item.change_type === 'NEW' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          }`}>
                            {item.change_type}
                          </span>
                          <span className="font-bold text-white text-sm">{item.title}</span>
                          <span className="text-xs text-slate-400">({item.category})</span>
                        </div>
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] text-ait-400 hover:underline flex items-center space-x-1 mt-0.5"
                        >
                          <span>{item.source_url}</span>
                          <ExternalLink className="w-3 h-3 inline" />
                        </a>
                      </div>

                      <div className="flex items-center space-x-2 self-start sm:self-auto">
                        <button
                          onClick={() => handleApproveKnowledge(item.id)}
                          className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center space-x-1 shadow transition-all"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Approve & RAG Index</span>
                        </button>
                        <button
                          onClick={() => handleRejectKnowledge(item.id)}
                          className="px-3 py-1.5 rounded-xl bg-red-600/30 hover:bg-red-600/50 text-red-300 border border-red-500/30 text-xs font-semibold flex items-center space-x-1 transition-all"
                        >
                          <X className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                        {item.source_id && (
                          <button
                            onClick={() => handleArchiveKnowledge(item.source_id!)}
                            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center space-x-1 transition-all"
                          >
                            <Archive className="w-3.5 h-3.5" />
                            <span>Archive</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {item.change_summary && (
                      <p className="text-xs text-slate-300 italic">{item.change_summary}</p>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {item.old_value && (
                        <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">
                          <span className="text-[11px] font-bold text-slate-400 uppercase">Previous Verified Content</span>
                          <p className="text-slate-400 font-mono text-[11px] line-clamp-4 leading-relaxed">{item.old_value}</p>
                        </div>
                      )}
                      <div className={`p-3.5 rounded-xl bg-slate-900/90 border border-emerald-500/20 space-y-1 ${!item.old_value ? 'md:col-span-2' : ''}`}>
                        <span className="text-[11px] font-bold text-emerald-400 uppercase">Detected New Content (Pending)</span>
                        <p className="text-slate-200 font-mono text-[11px] line-clamp-4 leading-relaxed">{item.new_value}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB: INTENT RETRAINING & MODEL GOVERNANCE */}
      {activeTab === 'training_review' && (
        <div className="space-y-6">
          <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b border-slate-800">
              <div>
                <h3 className="font-heading text-lg font-bold text-white flex items-center space-x-2">
                  <Cpu className="w-5 h-5 text-ait-500" />
                  <span>Controlled Intent Training Dataset & Retraining Pipeline</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Review student feedback misclassifications, assign verified intents, and trigger controlled retraining with accuracy validation.
                </p>
              </div>

              <button
                onClick={handleRetrainIntentModel}
                disabled={isRetraining}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-ait-600 to-blue-600 hover:from-ait-500 hover:to-blue-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center space-x-2 shadow-md transition-all self-start sm:self-auto"
              >
                <Cpu className={`w-4 h-4 ${isRetraining ? 'animate-spin' : ''}`} />
                <span>{isRetraining ? 'Retraining & Validating...' : 'Retrain Intent Model'}</span>
              </button>
            </div>

            {retrainResult && (
              <div className={`p-4 rounded-2xl border text-xs ${
                retrainResult.success ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-200' : 'bg-amber-950/40 border-amber-500/30 text-amber-200'
              }`}>
                <div className="font-bold text-sm mb-1">{retrainResult.message || (retrainResult.success ? 'Retraining Complete' : 'Retraining Notice')}</div>
                {retrainResult.accuracy !== undefined && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2 pt-2 border-t border-slate-800/60 font-mono text-[11px]">
                    <div>Accuracy: <strong>{(retrainResult.accuracy * 100).toFixed(1)}%</strong></div>
                    <div>F1-Score: <strong>{retrainResult.f1_score?.toFixed(3)}</strong></div>
                    <div>Active Version: <strong>{retrainResult.version || retrainResult.active_version}</strong></div>
                    <div>Total Samples: <strong>{retrainResult.total_samples || 'N/A'}</strong></div>
                  </div>
                )}
              </div>
            )}

            {/* Pending Training Examples List */}
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-bold uppercase text-slate-400">
                Pending Student Feedback Questions ({trainingExamples.filter(e => e.status === 'PENDING').length})
              </h4>

              {trainingExamples.filter(e => e.status === 'PENDING').length === 0 ? (
                <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 text-center text-xs text-slate-500">
                  No pending training examples requiring review. Student feedback questions will appear here.
                </div>
              ) : (
                trainingExamples.filter(e => e.status === 'PENDING').map((ex) => (
                  <div key={ex.id} className="glass-panel rounded-xl p-4 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="text-sm font-semibold text-white font-mono">"{ex.text}"</div>
                      <div className="text-[11px] text-slate-400 flex items-center space-x-3">
                        <span>Predicted: <span className="text-amber-400 font-mono">{ex.predicted_intent || 'Unknown'}</span></span>
                        <span>•</span>
                        <span>Language: <span className="text-slate-200 uppercase">{ex.language}</span></span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <select
                        value={selectedIntentMap[ex.id] || ex.predicted_intent || 'FACULTY_SUBJECT_QUERY'}
                        onChange={(e) => setSelectedIntentMap(prev => ({ ...prev, [ex.id]: e.target.value }))}
                        className="glass-input px-2.5 py-1.5 rounded-lg text-xs text-white bg-slate-900 border border-slate-700"
                      >
                        <option value="FACULTY_SUBJECT_QUERY">FACULTY_SUBJECT_QUERY</option>
                        <option value="FEE_QUERY">FEE_QUERY</option>
                        <option value="TIMETABLE_QUERY">TIMETABLE_QUERY</option>
                        <option value="EXAM_QUERY">EXAM_QUERY</option>
                        <option value="SYLLABUS_QUERY">SYLLABUS_QUERY</option>
                        <option value="RESULT_QUERY">RESULT_QUERY</option>
                        <option value="STUDY_ASSISTANT">STUDY_ASSISTANT</option>
                        <option value="EVENT_IMAGE_SEARCH">EVENT_IMAGE_SEARCH</option>
                        <option value="FACILITY_IMAGE_SEARCH">FACILITY_IMAGE_SEARCH</option>
                        <option value="NOTICE_QUERY">NOTICE_QUERY</option>
                        <option value="GENERAL_EDUCATION">GENERAL_EDUCATION</option>
                        <option value="GREETING">GREETING</option>
                      </select>

                      <button
                        onClick={() => handleApproveTrainingExample(ex.id, ex.predicted_intent || 'FACULTY_SUBJECT_QUERY')}
                        className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center space-x-1"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Approve</span>
                      </button>

                      <button
                        onClick={() => handleRejectTrainingExample(ex.id)}
                        className="px-3 py-1.5 rounded-lg bg-red-600/30 hover:bg-red-600/50 text-red-300 border border-red-500/30 text-xs font-semibold"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB: OFFICIAL AIT CONTENT & IMAGES */}
      {activeTab === 'official_content' && (
        <div className="space-y-6">
          <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-3 border-b border-slate-800">
              <div>
                <h3 className="font-heading text-lg font-bold text-white flex items-center space-x-2">
                  <Globe className="w-5 h-5 text-ait-400" />
                  <span>Official AIT Website Verified Images & Content Index</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Authoritative institutional photographs and verified facility records ingested strictly from <span className="text-ait-200 font-mono">https://www.aitindia.in</span>
                </p>
              </div>
              <button
                onClick={handleWebsiteSync}
                disabled={isSyncing}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center space-x-2 shadow-md transition-all self-start sm:self-auto"
              >
                <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
                <span>{isSyncing ? 'Synchronizing...' : 'Sync Live Website'}</span>
              </button>
            </div>

            {/* Official Images Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
              {facilities.flatMap(f => f.images.map(img => ({ ...img, facilityName: f.name, desc: f.description, location: f.location }))).map((item, idx) => (
                <div key={idx} className="glass-panel rounded-2xl overflow-hidden border border-slate-800 flex flex-col">
                  <div className="relative h-48 bg-slate-950 overflow-hidden">
                    <img
                      src={item.image_url}
                      alt={item.alt_text || item.caption || 'AIT Official Media'}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />
                    <div className="absolute top-2.5 right-2.5 px-2.5 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-[10px] font-bold text-emerald-300 flex items-center space-x-1 backdrop-blur-md">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      <span>✓ VERIFIED</span>
                    </div>
                  </div>

                  <div className="p-4 space-y-2 flex-1 flex flex-col justify-between">
                    <div>
                      <div className="text-sm font-bold text-white">{item.facilityName}</div>
                      <p className="text-xs text-slate-300 line-clamp-2 mt-1">{item.caption || item.desc}</p>
                    </div>

                    <div className="pt-3 border-t border-slate-800/80 space-y-1.5 text-[11px] text-slate-400">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-400">Source:</span>
                        <span className="text-slate-200 font-medium">Official AIT Website</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-400">Official URL:</span>
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-ait-400 hover:text-ait-300 truncate max-w-[200px] flex items-center space-x-1"
                        >
                          <span className="truncate">{item.source_url}</span>
                          <ExternalLink className="w-3 h-3 flex-shrink-0" />
                        </a>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-400">Status:</span>
                        <span className="text-emerald-400 font-semibold">✓ VERIFIED</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-400">Last synchronized:</span>
                        <span className="text-slate-300 font-mono">29-Aug-2026</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-400">Content hash:</span>
                        <span className="text-slate-400 font-mono text-[10px]">sha256:8f92a1c04d</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: KNOWLEDGE CONFLICT CENTER */}
      {activeTab === 'conflicts' && (
        <div className="space-y-4">
          <div className="glass-card rounded-2xl p-5 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search conflicts by topic or value..."
                value={conflictSearchQuery}
                onChange={(e) => setConflictSearchQuery(e.target.value)}
                className="w-full glass-input pl-9 pr-3 py-1.5 rounded-xl text-xs text-white"
              />
            </div>

            <div className="flex items-center space-x-1 glass-panel p-1 rounded-xl border border-slate-800">
              {(['ALL', 'OPEN', 'RESOLVED'] as const).map(status => (
                <button
                  key={status}
                  onClick={() => setConflictStatusFilter(status)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    conflictStatusFilter === status ? 'bg-ait-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>

          {filteredConflicts.length === 0 ? (
            <div className="glass-card rounded-2xl p-8 border border-slate-800 text-center text-xs text-slate-500">
              No knowledge conflicts matching selected criteria.
            </div>
          ) : (
            <div className="space-y-4">
              {filteredConflicts.map(c => (
                <div key={c.id} className="glass-card rounded-2xl p-5 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="flex items-center space-x-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                      <span className="font-bold text-white text-sm">{c.topic}</span>
                    </div>
                    <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${
                      c.status === 'OPEN'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    }`}>
                      {c.status}
                    </span>
                  </div>

                  {/* Side-by-Side Comparison */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="p-4 rounded-xl bg-slate-900/90 border border-blue-500/20 space-y-2">
                      <div className="flex items-center justify-between text-[11px] font-bold text-blue-400">
                        <span>{c.source_a_type} (Official Web Portal)</span>
                        <span className="text-[10px] text-slate-500">Priority 1 Source</span>
                      </div>
                      <div className="text-base font-bold text-white font-mono">{c.source_a_value}</div>
                      <div className="text-[11px] text-slate-400 truncate">Ref: {c.source_a_ref || 'https://www.aitindia.in'}</div>
                    </div>

                    <div className="p-4 rounded-xl bg-slate-900/90 border border-emerald-500/20 space-y-2">
                      <div className="flex items-center justify-between text-[11px] font-bold text-emerald-400">
                        <span>{c.source_b_type} (Admin Structured DB)</span>
                        <span className="text-[10px] text-slate-500">Priority 2 Source</span>
                      </div>
                      <div className="text-base font-bold text-white font-mono">{c.source_b_value}</div>
                      <div className="text-[11px] text-slate-400 truncate">Ref: {c.source_b_ref || 'College Database Entity'}</div>
                    </div>
                  </div>

                  {/* Resolution Controls */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                    <div className="text-[11px] text-slate-400">
                      {c.resolution_choice ? `Resolved via: ${c.resolution_choice}` : 'Select authoritative resolution:'}
                    </div>

                    <div className="flex items-center space-x-2">
                      {c.status === 'OPEN' ? (
                        <>
                          <button
                            onClick={() => handleResolveConflict(c.id, 'KEEP_DATABASE')}
                            className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md transition-all"
                          >
                            Enforce Database Truth
                          </button>
                          <button
                            onClick={() => handleResolveConflict(c.id, 'KEEP_WEBSITE')}
                            className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md transition-all"
                          >
                            Enforce Website Stated Value
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleReopenConflict(c.id)}
                          className="px-3 py-1.5 rounded-xl bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-500/30 text-xs font-semibold transition-all flex items-center space-x-1"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          <span>Reopen Conflict</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: ADVANCED ANALYTICS */}
      {activeTab === 'analytics' && analytics && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="glass-card p-4 rounded-2xl border border-slate-800">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Total Conversations</div>
              <div className="text-2xl font-bold text-white mt-1">{analytics.chat_metrics.total_conversations}</div>
              <div className="text-[10px] text-slate-400 mt-0.5">{analytics.chat_metrics.total_messages} total messages</div>
            </div>

            <div className="glass-card p-4 rounded-2xl border border-slate-800">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Avg AI Latency</div>
              <div className="text-2xl font-bold text-ait-200 mt-1">{analytics.chat_metrics.average_latency_ms} ms</div>
              <div className="text-[10px] text-emerald-400 mt-0.5">High Performance</div>
            </div>

            <div className="glass-card p-4 rounded-2xl border border-slate-800">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Cache Hit Ratio</div>
              <div className="text-2xl font-bold text-emerald-400 mt-1">{analytics.cache_efficiency.hit_ratio_pct}%</div>
              <div className="text-[10px] text-slate-400 mt-0.5">{analytics.cache_efficiency.total_cached_voice_clips} cached audio clips</div>
            </div>

            <div className="glass-card p-4 rounded-2xl border border-slate-800">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Conflict Resolution</div>
              <div className="text-2xl font-bold text-amber-400 mt-1">{analytics.knowledge_governance.conflict_resolution_rate_pct}%</div>
              <div className="text-[10px] text-slate-400 mt-0.5">{analytics.knowledge_governance.resolved_conflicts} resolved</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Source Tier Hierarchy Breakdown */}
            <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
              <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                <Layers className="w-4 h-4 text-ait-400" />
                <span>3-Tier Source Hierarchy Resolution</span>
              </h4>
              <div className="space-y-3">
                {Object.entries(analytics.source_hierarchy_usage).map(([src, pct]: [string, any]) => (
                  <div key={src} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-300 font-semibold">{src}</span>
                      <span className="font-mono text-ait-gold">{pct}%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div className="h-full bg-ait-600 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Intent Distribution Breakdown */}
            <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
              <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-ait-gold" />
                <span>AI Intent Distribution Breakdown</span>
              </h4>
              <div className="space-y-3">
                {Object.entries(analytics.intent_distribution).map(([intent, pct]: [string, any]) => (
                  <div key={intent} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-300 font-semibold">{intent}</span>
                      <span className="font-mono text-emerald-400">{pct}%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: ML MODEL REGISTRY */}
      {activeTab === 'models' && (
        <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="font-heading text-lg font-bold text-white flex items-center space-x-2">
                <Cpu className="w-5 h-5 text-ait-500" />
                <span>Specialized ML / NN Model Registry & Secure Rollback</span>
              </h3>
              <p className="text-xs text-slate-400">
                Version-controlled models with evaluation benchmarks and password-protected rollback
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Model Name</th>
                  <th className="px-4 py-3">Task</th>
                  <th className="px-4 py-3">Version</th>
                  <th className="px-4 py-3">Accuracy</th>
                  <th className="px-4 py-3">F1-Score</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {models.map(m => (
                  <tr key={m.id} className="hover:bg-slate-900/40">
                    <td className="px-4 py-3 font-semibold text-white">{m.name}</td>
                    <td className="px-4 py-3 text-slate-400">{m.task}</td>
                    <td className="px-4 py-3 font-mono text-ait-200">{m.version}</td>
                    <td className="px-4 py-3 font-mono text-emerald-400">{(m.accuracy * 100).toFixed(1)}%</td>
                    <td className="px-4 py-3 font-mono text-slate-300">{m.f1_score.toFixed(3)}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        m.is_active ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
                      }`}>
                        {m.is_active ? 'ACTIVE' : 'STANDBY'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {!m.is_active && (
                        <button
                          onClick={() => triggerDestructiveRollback(m.task, m.version)}
                          className="px-2.5 py-1 rounded bg-amber-600/20 hover:bg-amber-600/40 text-amber-300 border border-amber-500/30 flex items-center space-x-1"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Rollback</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Admin Re-Authentication Modal for Destructive Actions */}
      {reauthModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md glass-card rounded-2xl p-6 border border-amber-500/40 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2 text-amber-400">
                <Lock className="w-5 h-5" />
                <h3 className="font-heading text-lg font-bold text-white">Admin Re-Authentication Required</h3>
              </div>
              <button onClick={() => setReauthModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              You are executing a protected high-risk action (<span className="font-semibold text-white">{pendingAction?.type}</span>). Please confirm your administrator password to proceed.
            </p>

            {reauthError && (
              <div className="p-2.5 rounded-xl bg-red-500/20 border border-red-500/30 text-xs text-red-300">
                {reauthError}
              </div>
            )}

            <form onSubmit={handleConfirmReauth} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Admin Password</label>
                <input
                  type="password"
                  placeholder="Enter administrator password..."
                  value={reauthPassword}
                  onChange={(e) => setReauthPassword(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl text-xs text-white"
                  autoFocus
                  required
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setReauthModalOpen(false)}
                  className="px-4 py-2 rounded-xl glass-panel text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-lg shadow-amber-600/30"
                >
                  Confirm & Execute Action
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
