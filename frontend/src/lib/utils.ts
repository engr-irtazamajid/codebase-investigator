import { AuditResult } from '@/types';

export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function verdictColor(verdict: AuditResult['verdict']): string {
  return {
    reliable: 'text-emerald-400',
    caution: 'text-amber-400',
    unreliable: 'text-rose-400',
  }[verdict];
}

export function verdictBg(verdict: AuditResult['verdict']): string {
  return {
    reliable: 'bg-emerald-400/10 border-emerald-400/30',
    caution: 'bg-amber-400/10 border-amber-400/30',
    unreliable: 'bg-rose-400/10 border-rose-400/30',
  }[verdict];
}

export function verdictLabel(verdict: AuditResult['verdict']): string {
  return { reliable: 'Reliable', caution: 'Caution', unreliable: 'Unreliable' }[verdict];
}

export function severityColor(severity: string): string {
  return { low: 'text-sky-400', medium: 'text-amber-400', high: 'text-rose-400' }[severity] ?? 'text-slate-400';
}

export function trustScoreGradient(score: number): string {
  if (score >= 8) return 'from-emerald-500 to-emerald-400';
  if (score >= 5) return 'from-amber-500 to-amber-400';
  return 'from-rose-500 to-rose-400';
}

/** Detect the language from a file path extension for syntax coloring hints. */
export function langFromPath(filePath: string): string {
  const ext = filePath.split('.').pop() ?? '';
  const map: Record<string, string> = {
    py: 'python', js: 'javascript', ts: 'typescript', tsx: 'tsx', jsx: 'jsx',
    go: 'go', rs: 'rust', java: 'java', cs: 'csharp', rb: 'ruby',
    md: 'markdown', json: 'json', yaml: 'yaml', yml: 'yaml', sh: 'bash',
    css: 'css', html: 'html', sql: 'sql',
  };
  return map[ext] ?? 'text';
}

/** Strip [[file:line-line]] citation markers from displayed text. */
export function stripCitationMarkers(text: string): string {
  return text.replace(/\[\[[^\]]+\]\]/g, '');
}
