import React, { useEffect, useState } from 'react';
import { FileText, Search, Trash2, Upload, X } from 'lucide-react';
import { api } from '../services/api';

interface LibraryViewProps { onUseInChat?: (id: string) => void; }

export const LibraryView: React.FC<LibraryViewProps> = ({ onUseInChat }) => {
  const [items, setItems] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try { const data = await api.getLibrary(search, page, 20); setItems(data.items || []); setTotal(data.total || 0); }
    catch (err: any) { setError(err.message || 'Unable to load your Library.'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [search, page]);
  const remove = async (id: string) => {
    try { await api.deleteAttachment(id); setItems(current => current.filter(item => item.id !== id)); setTotal(value => Math.max(0, value - 1)); }
    catch (err: any) { setError(err.message || 'Unable to delete this attachment.'); }
  };
  const open = async (id: string) => {
    try { const item = await api.getAttachment(id); const blob = new Blob([item.content || ''], { type: 'text/plain' }); window.open(URL.createObjectURL(blob), '_blank', 'noopener,noreferrer'); }
    catch (err: any) { setError(err.message || 'Attachment not found.'); }
  };
  return <section className="w-full max-w-5xl mx-auto px-4 sm:px-6 py-6">
    <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div><h1 className="text-2xl font-bold text-white">Library</h1><p className="text-sm text-slate-400">Your uploaded study files</p></div>
      <label className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-ait-600 text-white text-sm font-semibold cursor-pointer"><Upload className="w-4 h-4" />Upload file<input className="hidden" type="file" onChange={async e => { const file = e.target.files?.[0]; if (!file) return; try { await api.uploadAttachment(file); setPage(1); await load(); } catch (err: any) { setError(err.message || 'Upload failed.'); } e.target.value = ''; }} /></label>
    </div>
    <div className="relative mb-4"><Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" /><input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Search files" aria-label="Search Library" className="w-full rounded-lg border-slate-800 bg-slate-900 px-9 py-2 text-sm text-white outline-none focus:border-ait-500" /></div>
    {error && <div role="alert" className="mb-4 flex items-center justify-between rounded-lg border-red-500/30 bg-red-950/30 px-3 py-2 text-sm text-red-200"><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}><X className="w-4 h-4" /></button></div>}
    {loading ? <p className="text-sm text-slate-400">Loading Library...</p> : items.length === 0 ? <p className="text-sm text-slate-400">No uploaded files yet.</p> : <div className="divide-y divide-slate-800 rounded-lg border-slate-800 bg-slate-900/70">{items.map(item => <div key={item.id} className="flex flex-wrap items-center gap-3 px-4 py-3"><FileText className="w-5 h-5 text-ait-gold" /><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-white">{item.filename}</p><p className="text-xs text-slate-500">{item.type} · {Math.round(item.size / 1024)} KB · {item.processing_status}</p></div><button onClick={() => open(item.id)} className="text-xs text-blue-300 hover:text-white">Open</button><button onClick={() => onUseInChat?.(item.id)} className="text-xs text-blue-300 hover:text-white">Use in chat</button><button onClick={() => remove(item.id)} aria-label={`Delete ${item.filename}`} title="Delete file" className="p-1 text-slate-400 hover:text-red-300"><Trash2 className="w-4 h-4" /></button></div>)}</div>}
    {total > 20 && <div className="mt-4 flex items-center justify-between text-sm text-slate-400"><span>{total} files</span><div className="flex gap-2"><button disabled={page === 1} onClick={() => setPage(value => value - 1)} className="rounded border-slate-700 px-3 py-1 disabled:opacity-40">Previous</button><button disabled={page * 20 >= total} onClick={() => setPage(value => value + 1)} className="rounded border-slate-700 px-3 py-1 disabled:opacity-40">Next</button></div></div>}
  </section>;
};