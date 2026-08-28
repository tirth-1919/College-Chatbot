import React, { useState, useEffect } from 'react';
import { DashboardMetrics, KnowledgeConflict, MLModelItem } from '../types';
import { api } from '../services/api';
import {
  ShieldAlert, RefreshCw, AlertTriangle, Cpu, History, DollarSign,
  CheckCircle2, RotateCcw, Activity, Database, Check
} from 'lucide-react';

export const AdminView: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [conflicts, setConflicts] = useState<KnowledgeConflict[]>([]);
  const [models, setModels] = useState<MLModelItem[]>([]);
  const [bcaFeeInput, setBcaFeeInput] = useState<string>('32000');
  const [feeSaveSuccess, setFeeSaveSuccess] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);

  useEffect(() => {
    loadAdminData();
  }, []);

  const loadAdminData = async () => {
    try {
      const [m, c, mdl] = await Promise.all([
        api.getMetrics(),
        api.getConflicts(),
        api.getMLModels(),
      ]);
      setMetrics(m);
      setConflicts(c);
      setModels(mdl);
    } catch (err) {
      console.error('Error loading admin data:', err);
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

  const handleRollback = async (task: string, version: string) => {
    try {
      await api.rollbackModel(task, version);
      loadAdminData();
    } catch (err) {
      console.error('Failed to rollback model:', err);
    }
  };

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
            Manage official source sync, knowledge conflict resolutions, deterministic fee updates, and ML model rollbacks
          </p>
        </div>

        <button
          onClick={handleWebsiteSync}
          disabled={isSyncing}
          className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center space-x-2 shadow-md shadow-blue-600/30 transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
          <span>{isSyncing ? 'Synchronizing...' : 'Sync AIT Website (aitindia.in)'}</span>
        </button>
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

      {/* 1. Direct Academic Data Modifier (BCA Fees) */}
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

      {/* 2. Knowledge Conflict Center */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 className="font-heading text-lg font-bold text-white flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              <span>Knowledge Conflict Center</span>
            </h3>
            <p className="text-xs text-slate-400">
              When public website and verified database values differ, resolve the authoritative source here
            </p>
          </div>
        </div>

        {conflicts.length === 0 ? (
          <div className="text-center py-6 text-xs text-slate-500">
            No active knowledge conflicts detected across authoritative sources.
          </div>
        ) : (
          <div className="space-y-3">
            {conflicts.map(c => (
              <div key={c.id} className="glass-panel p-4 rounded-xl border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white text-xs">{c.topic}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {c.status}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] text-blue-400 font-bold block">{c.source_a_type} (Portal)</span>
                    <span className="text-sm font-bold text-slate-200">{c.source_a_value}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] text-emerald-400 font-bold block">{c.source_b_type} (Admin DB)</span>
                    <span className="text-sm font-bold text-slate-200">{c.source_b_value}</span>
                  </div>
                </div>

                {c.status === 'OPEN' && (
                  <div className="flex items-center space-x-2 pt-2">
                    <button
                      onClick={() => handleResolveConflict(c.id, 'KEEP_DATABASE')}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/30 text-xs font-medium"
                    >
                      Enforce Database Truth
                    </button>
                    <button
                      onClick={() => handleResolveConflict(c.id, 'KEEP_WEBSITE')}
                      className="px-3 py-1.5 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/30 text-xs font-medium"
                    >
                      Enforce Website Stated Value
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3. ML Model Registry & Instant Rollback */}
      <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 className="font-heading text-lg font-bold text-white flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-ait-500" />
              <span>Specialized ML / NN Model Registry & Rollback</span>
            </h3>
            <p className="text-xs text-slate-400">
              Version-controlled models with evaluation benchmarks and one-click rollback
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
                        onClick={() => handleRollback(m.task, m.version)}
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
    </div>
  );
};
