'use client';

import { useEffect, useState } from 'react';
import { useConversationStore } from '@/store/conversation';
import RepoInput from '@/components/repo/RepoInput';
import ChatInterface from '@/components/chat/ChatInterface';
import { BookOpen, FileCode2, Layers } from 'lucide-react';

export default function Home() {
  const { repoInfo, sessionId, reset } = useConversationStore();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  // Prevent SSR/client mismatch — Zustand state is client-only
  if (!mounted) return null;

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="shrink-0 border-b border-slate-800 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-indigo-400" />
            </div>
            <span className="font-semibold text-slate-100">CodeInvestigator</span>
          </div>

          {repoInfo ? (
            <div className="flex items-center gap-4 ml-auto">
              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span className="flex items-center gap-1.5">
                  <FileCode2 className="w-3.5 h-3.5" />
                  {repoInfo.files_indexed} files
                </span>
                <span className="flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" />
                  {repoInfo.chunks_indexed} chunks
                </span>
                <span className="bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-full px-3 py-1 font-mono font-medium">
                  {repoInfo.repo_name}
                </span>
              </div>
              <button
                onClick={reset}
                className="text-xs text-slate-500 hover:text-slate-300 transition-colors border border-slate-700 hover:border-slate-600 rounded-lg px-3 py-1.5"
              >
                New repo
              </button>
            </div>
          ) : (
            <p className="ml-auto text-xs text-slate-500">
              Paste a GitHub URL to start investigating
            </p>
          )}
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-hidden max-w-5xl w-full mx-auto flex flex-col">
        {!sessionId ? (
          /* Landing */
          <div className="flex-1 flex flex-col items-center justify-center gap-10 px-6 py-12">
            <div className="text-center space-y-3">
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">
                Investigate any GitHub repo
              </h1>
              <p className="text-slate-400 max-w-lg text-sm leading-relaxed">
                Paste a public GitHub URL, ask questions in plain English, and get
                answers grounded in specific files and line ranges — each with an
                independent audit you can trust.
              </p>
            </div>

            <RepoInput />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl w-full text-center">
              {[
                { title: 'Grounded answers', desc: 'Every claim cites exact files and line ranges.' },
                { title: 'Independent audit', desc: 'A separate model call checks each answer — no self-scoring.' },
                { title: 'Coherent conversation', desc: 'Prior claims tracked and surfaced for contradiction detection.' },
              ].map((f) => (
                <div
                  key={f.title}
                  className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 text-sm"
                >
                  <p className="font-semibold text-slate-200 mb-1">{f.title}</p>
                  <p className="text-slate-500 text-xs leading-relaxed">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Chat */
          <ChatInterface />
        )}
      </main>
    </div>
  );
}
