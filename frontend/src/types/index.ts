// ── Domain types shared across the app ────────────────────────────────────────

export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  content: string;
  relevance_score: number;
}

export interface AuditFlag {
  type: 'citation_invalid' | 'overconfident' | 'scope_creep' | 'contradiction' | 'missing_evidence';
  description: string;
  severity: 'low' | 'medium' | 'high';
}

export interface AuditResult {
  trust_score: number;   // 0–10
  verdict: 'reliable' | 'caution' | 'unreliable';
  flags: AuditFlag[];
  summary: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  audit?: AuditResult;
  turn: number;
  isStreaming?: boolean;
}

export interface RepoInfo {
  session_id: string;
  repo_name: string;
  files_indexed: number;
  chunks_indexed: number;
}

// ── SSE stream event shapes ────────────────────────────────────────────────────

export type StreamEvent =
  | { type: 'token'; content: string }
  | { type: 'citations'; data: Citation[] }
  | { type: 'audit'; data: AuditResult }
  | { type: 'error'; message: string };
