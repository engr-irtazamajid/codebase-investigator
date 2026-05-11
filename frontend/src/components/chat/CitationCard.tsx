'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, ExternalLink, FileCode } from 'lucide-react';
import { Citation } from '@/types';
import { fetchFileContent } from '@/lib/api';
import { useConversationStore } from '@/store/conversation';

interface Props {
  citation: Citation;
  index: number;
}

export default function CitationCard({ citation, index }: Props) {
  const { sessionId } = useConversationStore();
  const [expanded, setExpanded] = useState(false);
  const [fullContent, setFullContent] = useState<string | null>(null);
  const [loadingFull, setLoadingFull] = useState(false);

  const shortPath =
    citation.file_path.length > 50
      ? '…' + citation.file_path.slice(-47)
      : citation.file_path;

  const scorePercent = Math.round(citation.relevance_score * 100);

  const loadFullFile = async () => {
    if (fullContent || !sessionId) return;
    setLoadingFull(true);
    try {
      const data = await fetchFileContent(sessionId, citation.file_path);
      setFullContent(data.content);
    } catch {
      setFullContent('// Could not load file content');
    } finally {
      setLoadingFull(false);
    }
  };

  const handleExpand = () => {
    setExpanded((v) => !v);
    if (!expanded) loadFullFile();
  };

  const renderContent = () => {
    const source = fullContent ?? citation.content;
    const lines = source.split('\n');
    const startOffset = fullContent ? 0 : citation.start_line - 1;

    return lines.map((line, i) => {
      const lineNum = startOffset + i + 1;
      const highlighted =
        lineNum >= citation.start_line && lineNum <= citation.end_line;
      return (
        <div
          key={i}
          className={`flex ${highlighted ? 'bg-indigo-500/10 border-l-2 border-indigo-400' : ''}`}
        >
          <span className="select-none text-slate-600 text-xs w-10 shrink-0 text-right pr-3 py-0.5 font-mono">
            {lineNum}
          </span>
          <span className="text-xs font-mono text-slate-300 py-0.5 whitespace-pre">
            {line}
          </span>
        </div>
      );
    });
  };

  return (
    <div className="rounded-lg border border-slate-700/60 bg-slate-800/50 overflow-hidden text-xs">
      <button
        onClick={handleExpand}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-700/40 transition-colors text-left"
      >
        <span className="text-indigo-400 font-mono font-semibold shrink-0">
          [{index + 1}]
        </span>
        <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span className="text-slate-300 font-mono flex-1 truncate" title={citation.file_path}>
          {shortPath}
        </span>
        <span className="text-slate-500 shrink-0">
          L{citation.start_line}–{citation.end_line}
        </span>
        <span
          className="shrink-0 px-1.5 py-0.5 rounded text-slate-400 bg-slate-700"
          title="Relevance score"
        >
          {scorePercent}%
        </span>
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-slate-700/60 overflow-x-auto max-h-64 overflow-y-auto bg-slate-900">
          {loadingFull ? (
            <p className="text-slate-500 px-4 py-3 font-mono">Loading…</p>
          ) : (
            <div className="py-1">{renderContent()}</div>
          )}
        </div>
      )}
    </div>
  );
}
