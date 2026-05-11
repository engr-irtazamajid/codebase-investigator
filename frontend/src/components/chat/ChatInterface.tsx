'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowUp, Loader2 } from 'lucide-react';
import { streamChat } from '@/lib/api';
import { useConversationStore } from '@/store/conversation';
import { Message } from '@/types';
import MessageBubble from './MessageBubble';

const EXAMPLE_QUESTIONS = [
  'How does authentication work here?',
  "Is there dead code? What's safe to delete?",
  'Suggest a better way to handle errors in the API layer.',
  'Walk me through what this service does. Skip the obvious.',
];

export default function ChatInterface() {
  const { sessionId, messages, isLoading, addMessage, updateMessage, setLoading, setError } =
    useConversationStore();

  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const submit = async (question: string) => {
    const q = question.trim();
    if (!q || !sessionId || isLoading) return;

    setInput('');
    setError(null);
    setLoading(true);

    const turn = Math.floor(messages.length / 2) + 1;

    addMessage({ id: crypto.randomUUID(), role: 'user', content: q, turn });

    const assistantId = crypto.randomUUID();
    addMessage({ id: assistantId, role: 'assistant', content: '', turn, isStreaming: true });

    let accumulated = '';

    try {
      for await (const event of streamChat(sessionId, q)) {
        if (event.type === 'token') {
          accumulated += event.content;
          updateMessage(assistantId, { content: accumulated });
        } else if (event.type === 'citations') {
          updateMessage(assistantId, { citations: event.data });
        } else if (event.type === 'audit') {
          updateMessage(assistantId, { audit: event.data, isStreaming: false });
        } else if (event.type === 'error') {
          updateMessage(assistantId, { content: `Error: ${event.message}`, isStreaming: false });
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Request failed';
      updateMessage(assistantId, { content: `Error: ${msg}`, isStreaming: false });
      setError(msg);
    } finally {
      updateMessage(assistantId, { isStreaming: false });
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <p className="text-slate-500 text-sm">
              Ask anything about this codebase. Every answer ships with an independent audit.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => submit(q)}
                  className="text-left text-xs text-slate-400 bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700/60 rounded-xl px-3 py-2.5 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-slate-800 px-4 py-4 bg-slate-950">
        <div className="max-w-3xl mx-auto flex items-end gap-2">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the codebase… (Shift+Enter for newline)"
            disabled={isLoading}
            className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none transition disabled:opacity-50"
            style={{ minHeight: '48px', maxHeight: '160px' }}
          />
          <button
            onClick={() => submit(input)}
            disabled={isLoading || !input.trim()}
            className="shrink-0 w-11 h-11 flex items-center justify-center bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 text-white animate-spin" />
            ) : (
              <ArrowUp className="w-4 h-4 text-white" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
