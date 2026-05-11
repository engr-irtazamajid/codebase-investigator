'use client';

import { useState } from 'react';
import { GitBranch, Loader2, Search } from 'lucide-react';
import { ingestRepo } from '@/lib/api';
import { useConversationStore } from '@/store/conversation';

export default function RepoInput() {
  const [url, setUrl] = useState('');
  const { setSession, setIngesting, setError, isIngesting, error } =
    useConversationStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) return;

    setError(null);
    setIngesting(true);
    try {
      const info = await ingestRepo(trimmed);
      setSession(info.session_id, info);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ingestion failed');
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
            className="w-full pl-10 pr-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-sm"
            disabled={isIngesting}
            required
          />
        </div>
        <button
          type="submit"
          disabled={isIngesting || !url.trim()}
          className="flex items-center gap-2 px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-medium text-sm transition-colors"
        >
          {isIngesting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          {isIngesting ? 'Indexing…' : 'Investigate'}
        </button>
      </form>

      {error && (
        <p className="mt-3 text-sm text-rose-400 bg-rose-400/10 border border-rose-400/20 rounded-lg px-4 py-2">
          {error}
        </p>
      )}
    </div>
  );
}
