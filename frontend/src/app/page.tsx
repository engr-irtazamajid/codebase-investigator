'use client';

import { useSyncExternalStore } from 'react';
import { useConversationStore } from '@/store/conversation';
import RepoInput from '@/components/repo/RepoInput';
import ChatInterface from '@/components/chat/ChatInterface';
import { BookOpen, FileCode2, Layers, ShieldCheck, MessageSquare } from 'lucide-react';

const useIsClient = () =>
  useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );

const FEATURES = [
  {
    icon: FileCode2,
    title: 'Grounded answers',
    desc: 'Every claim cites exact files and line ranges — expandable inline.',
    color: 'text-indigo-400',
    bg: 'bg-indigo-500/10 border-indigo-500/20',
  },
  {
    icon: ShieldCheck,
    title: 'Independent audit',
    desc: 'A separate LLM call with no conversation history checks each answer.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10 border-emerald-500/20',
  },
  {
    icon: MessageSquare,
    title: 'Coherent over 15 turns',
    desc: 'Prior claims tracked and surfaced so contradictions get caught.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10 border-amber-500/20',
  },
];

export default function Home() {
  const { repoInfo, sessionId, reset } = useConversationStore();
  const isClient = useIsClient();

  if (!isClient) return null;

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100">

      {/* Header */}
      <header className="shrink-0 border-b border-slate-800/60 px-6 py-3.5 backdrop-blur-sm bg-slate-950/80 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-indigo-600/25 border border-indigo-500/40 flex items-center justify-center">
              <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
            </div>
            <span className="font-semibold text-sm text-slate-100">CodeInvestigator</span>
          </div>

          {repoInfo ? (
            <div className="flex items-center gap-3 ml-auto">
              <div className="hidden sm:flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <FileCode2 className="w-3 h-3" />
                  {repoInfo.files_indexed} files
                </span>
                <span className="flex items-center gap-1">
                  <Layers className="w-3 h-3" />
                  {repoInfo.chunks_indexed} chunks
                </span>
              </div>
              <span className="bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 rounded-full px-3 py-1 text-xs font-mono">
                {repoInfo.repo_name}
              </span>
              <button
                onClick={reset}
                className="text-xs text-slate-500 hover:text-slate-300 transition-colors border border-slate-700/60 hover:border-slate-600 rounded-lg px-3 py-1.5"
              >
                New repo
              </button>
            </div>
          ) : (
            <span className="ml-auto text-xs text-slate-600 hidden sm:block">
              Public GitHub repos only
            </span>
          )}
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 w-full mx-auto max-w-5xl flex flex-col">
        {!sessionId ? (
          <div className="flex-1 flex flex-col items-center justify-center px-6 py-16 gap-12">

            {/* Hero */}
            <div className="text-center space-y-4 max-w-2xl">
              <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 text-xs text-indigo-400 font-medium mb-2">
                <ShieldCheck className="w-3.5 h-3.5" />
                Every answer ships with an independent audit
              </div>
              <h1 className="text-4xl sm:text-5xl font-bold tracking-tight bg-gradient-to-b from-slate-100 to-slate-400 bg-clip-text text-transparent leading-tight">
                Investigate any<br />GitHub repo
              </h1>
              <p className="text-slate-400 text-base leading-relaxed">
                Paste a public GitHub URL, ask questions in plain English, and get
                answers grounded in specific files and line ranges.
              </p>
            </div>

            {/* Input */}
            <div className="w-full max-w-xl">
              <RepoInput />
            </div>

            {/* Feature cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-3xl">
              {FEATURES.map(({ icon: Icon, title, desc, color, bg }) => (
                <div
                  key={title}
                  className={`rounded-xl border p-5 text-left space-y-2.5 ${bg}`}
                >
                  <div className={`w-8 h-8 rounded-lg bg-slate-900/60 flex items-center justify-center`}>
                    <Icon className={`w-4 h-4 ${color}`} />
                  </div>
                  <p className="font-semibold text-slate-200 text-sm">{title}</p>
                  <p className="text-slate-500 text-xs leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>

            {/* Example repos */}
            <div className="flex flex-wrap gap-2 justify-center">
              <span className="text-xs text-slate-600 self-center">Try with:</span>
              {[
                'tiangolo/fastapi',
                'vercel/next.js',
                'pallets/flask',
              ].map((repo) => (
                <button
                  key={repo}
                  onClick={() => {
                    const input = document.querySelector('input[type="url"]') as HTMLInputElement;
                    if (input) {
                      input.value = `https://github.com/${repo}`;
                      input.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                  }}
                  className="text-xs font-mono text-slate-400 hover:text-indigo-400 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-indigo-500/30 rounded-lg px-3 py-1.5 transition-all"
                >
                  {repo}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ChatInterface />
        )}
      </main>
    </div>
  );
}
