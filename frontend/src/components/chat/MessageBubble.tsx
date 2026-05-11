'use client';

import { useState } from 'react';
import { Bot, ChevronDown, ChevronUp, User } from 'lucide-react';
import { Message } from '@/types';
import { stripCitationMarkers } from '@/lib/utils';
import AuditPanel from './AuditPanel';
import CitationCard from './CitationCard';

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const [citationsOpen, setCitationsOpen] = useState(false);
  const isAssistant = message.role === 'assistant';

  const displayText = isAssistant
    ? stripCitationMarkers(message.content)
    : message.content;

  return (
    <div className={`flex gap-3 ${isAssistant ? '' : 'flex-row-reverse'}`}>
      <div
        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm ${
          isAssistant
            ? 'bg-indigo-600/30 text-indigo-400 border border-indigo-500/30'
            : 'bg-slate-700 text-slate-300 border border-slate-600'
        }`}
      >
        {isAssistant ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
      </div>

      <div className={`flex-1 max-w-3xl space-y-2 ${isAssistant ? '' : 'items-end flex flex-col'}`}>
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
            isAssistant
              ? 'bg-slate-800 text-slate-100 rounded-tl-sm border border-slate-700/60'
              : 'bg-indigo-600 text-white rounded-tr-sm'
          }`}
        >
          {displayText}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-4 bg-indigo-400 ml-1 animate-pulse rounded-sm align-middle" />
          )}
        </div>

        {isAssistant && message.citations && message.citations.length > 0 && (
          <div className="space-y-1.5 w-full">
            <button
              onClick={() => setCitationsOpen((v) => !v)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              {citationsOpen ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
              {message.citations.length} source
              {message.citations.length !== 1 ? 's' : ''}
            </button>

            {citationsOpen && (
              <div className="space-y-1.5">
                {message.citations.map((c, i) => (
                  <CitationCard key={`${c.file_path}-${c.start_line}`} citation={c} index={i} />
                ))}
              </div>
            )}
          </div>
        )}

        {isAssistant && message.audit && !message.isStreaming && (
          <div className="w-full">
            <AuditPanel audit={message.audit} />
          </div>
        )}

        {isAssistant && !message.audit && !message.isStreaming && message.content && (
          <div className="w-full rounded-lg border border-slate-700/40 bg-slate-800/30 px-3 py-2 text-xs text-slate-500">
            Running independent audit…
          </div>
        )}
      </div>
    </div>
  );
}
