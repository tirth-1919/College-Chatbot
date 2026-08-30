import React, { useEffect, useState } from 'react';
import { MarkdownRenderer } from './MarkdownRenderer';

export const ShareView: React.FC<{ token: string }> = ({ token }) => {
  const [data, setData] = useState<any>(null); const [error, setError] = useState('');
  useEffect(() => { fetch(`/api/v1/shares/${encodeURIComponent(token)}`).then(async res => { if (!res.ok) throw new Error('This shared conversation is unavailable.'); return res.json(); }).then(setData).catch((err: any) => setError(err.message)); }, [token]);
  if (error) return <main className="mx-auto max-w-2xl p-8 text-center text-red-200">{error}</main>;
  if (!data) return <main className="mx-auto max-w-2xl p-8 text-center text-slate-400">Loading shared conversation...</main>;
  return <main className="mx-auto max-w-3xl p-4 sm:p-8"><h1 className="mb-6 text-2xl font-bold text-white">{data.title}</h1><div className="space-y-5">{data.messages.map((message: any, index: number) => <article key={index} className="rounded-lg border-slate-800 bg-slate-900/70 p-4"><p className="mb-2 text-xs font-semibold uppercase text-slate-500">{message.role === 'user' ? 'Question' : 'AIT AI Assistant'}</p>{message.role === 'assistant' ? <MarkdownRenderer content={message.content} /> : <p className="whitespace-pre-wrap text-slate-200">{message.content}</p>}</article>)}</div></main>;
};