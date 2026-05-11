'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react';
import { AuditResult } from '@/types';
import { cn, severityColor, trustScoreGradient, verdictBg, verdictColor, verdictLabel } from '@/lib/utils';

const FLAG_LABELS: Record<string, string> = {
  citation_invalid: 'Invalid citation',
  overconfident: 'Over-confident',
  scope_creep: 'Scope creep',
  contradiction: 'Contradiction',
  missing_evidence: 'Missing evidence',
};

const VerdictIcon = ({ verdict }: { verdict: AuditResult['verdict'] }) => {
  if (verdict === 'reliable') return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
  if (verdict === 'unreliable') return <ShieldX className="w-4 h-4 text-rose-400" />;
  return <ShieldAlert className="w-4 h-4 text-amber-400" />;
};

interface Props {
  audit: AuditResult;
}

export default function AuditPanel({ audit }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className={cn('rounded-lg border text-xs overflow-hidden', verdictBg(audit.verdict))}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2.5 px-3 py-2 hover:bg-white/5 transition-colors text-left"
      >
        <VerdictIcon verdict={audit.verdict} />

        <span className="font-semibold uppercase tracking-wide text-[10px] text-slate-400">
          Audit
        </span>

        <span className={cn('font-semibold', verdictColor(audit.verdict))}>
          {verdictLabel(audit.verdict)}
        </span>

        <div className="flex items-center gap-1.5 ml-auto">
          <div className="w-16 h-1.5 rounded-full bg-slate-700 overflow-hidden">
            <div
              className={cn('h-full rounded-full bg-gradient-to-r', trustScoreGradient(audit.trust_score))}
              style={{ width: `${audit.trust_score * 10}%` }}
            />
          </div>
          <span className="text-slate-300 font-mono">{audit.trust_score}/10</span>
        </div>

        {audit.flags.length > 0 && (
          <span className="bg-rose-500/20 text-rose-400 rounded px-1.5 py-0.5 font-mono">
            {audit.flags.length} flag{audit.flags.length !== 1 ? 's' : ''}
          </span>
        )}

        {open ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        )}
      </button>

      {open && (
        <div className="border-t border-white/10 px-3 py-3 space-y-3">
          <p className="text-slate-300 leading-relaxed">{audit.summary}</p>

          {audit.flags.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-slate-500 uppercase tracking-wide text-[10px] font-semibold">
                Flags
              </p>
              {audit.flags.map((flag, i) => (
                <div
                  key={i}
                  className="flex gap-2 bg-slate-900/40 rounded px-2.5 py-2"
                >
                  <span className={cn('font-semibold shrink-0 uppercase text-[10px] pt-0.5', severityColor(flag.severity))}>
                    {flag.severity}
                  </span>
                  <div>
                    <span className="text-slate-300 font-medium">
                      {FLAG_LABELS[flag.type] ?? flag.type}
                    </span>
                    {' — '}
                    <span className="text-slate-400">{flag.description}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
