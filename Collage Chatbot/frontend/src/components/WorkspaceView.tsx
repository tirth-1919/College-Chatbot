import React, { useEffect, useState } from 'react';
import { Plus, FolderKanban, FileText, Save, Download } from 'lucide-react';
import { api } from '../services/api';
import { MarkdownRenderer } from './MarkdownRenderer';

export const WorkspaceView: React.FC = () => {
  const [projects, setProjects] = useState<any[]>([]); const [active, setActive] = useState<any>(null);
  const [name, setName] = useState(''); const [instructions, setInstructions] = useState(''); const [canvas, setCanvas] = useState<any>(null); const [content, setContent] = useState(''); const [error, setError] = useState('');
  const load = async () => {
    try { const result = await api.getProjects(); setProjects(result.items || []); } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);
  const create = async () => {
    if (!name.trim()) return; try { const item = await api.createProject({ name, instructions }); setProjects(items => [item, ...items]); setActive(item); setName(''); } catch (e: any) { setError(e.message); }
  };
  const openCanvas = async () => {
    if (!active) return; try { const result = await api.createCanvas(active.id, { title: 'Working Canvas', content: '' }); setCanvas(result); setContent(result.content); } catch (e: any) { setError(e.message); }
  };
  const save = async () => {
    if (!canvas) return; try { const result = await api.updateCanvas(canvas.id, { title: canvas.title, content, content_type: canvas.content_type }); setCanvas(result); } catch (e: any) { setError(e.message); }
  };
  const exportCanvas = () => { if (canvas) window.open(`/api/v1/workspace/canvases/${encodeURIComponent(canvas.id)}/export?format=md`, '_blank', 'noopener,noreferrer'); };
  return <section className="w-full max-w-5xl mx-auto px-4 sm:px-6 py-6"><div className="flex items-center justify-between mb-5"><div><h1 className="text-2xl font-bold text-white">Projects</h1><p className="text-sm text-slate-400">Organize chats, files, and canvases</p></div><button onClick={create} className="flex items-center gap-2 rounded-lg bg-ait-600 px-3 py-2 text-sm font-semibold text-white"><Plus className="w-4 h-4" />Create project</button></div><div className="grid gap-4 md:grid-cols-[240px_1fr]"><aside className="space-y-2"><input value={name} onChange={e => setName(e.target.value)} placeholder="New project name" aria-label="New project name" className="w-full rounded-lg border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white" /><textarea value={instructions} onChange={e => setInstructions(e.target.value)} placeholder="Project instructions" aria-label="Project instructions" rows={3} className="w-full rounded-lg border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white" />{projects.map(item => <button key={item.id} onClick={() => setActive(item)} className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm ${active?.id === item.id ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-900'}`}><FolderKanban className="w-4 h-4" />{item.name}</button>)}</aside><main className="rounded-lg border-slate-800 bg-slate-900/70 p-4">{active ? <><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold text-white">{active.name}</h2><button onClick={openCanvas} className="flex items-center gap-2 rounded border-slate-700 px-3 py-1.5 text-sm text-slate-200"><FileText className="w-4 h-4" />New Canvas</button></div>{active.instructions && <p className="mt-3 text-sm text-slate-400">{active.instructions}</p>}{canvas && <div className="mt-5"><textarea value={content} onChange={e => setContent(e.target.value)} aria-label="Canvas content" className="min-h-[320px] w-full rounded-lg border-slate-800 bg-slate-950 p-3 font-mono text-sm text-slate-100" /><div className="mt-2 flex gap-2"><button onClick={save} className="flex items-center gap-2 rounded bg-ait-600 px-3 py-2 text-sm text-white"><Save className="w-4 h-4" />Save</button><button onClick={exportCanvas} className="flex items-center gap-2 rounded border-slate-700 px-3 py-2 text-sm text-slate-200"><Download className="w-4 h-4" />Export</button></div><div className="sr-only"><MarkdownRenderer content={content} /></div></div>}</> : <p className="text-sm text-slate-400">Select or create a project.</p>}</main></div>{error && <p role="alert" className="mt-4 text-sm text-red-300">{error}</p>}</section>;
};