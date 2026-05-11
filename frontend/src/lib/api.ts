import { Citation, AuditResult, RepoInfo, StreamEvent } from '@/types';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function ingestRepo(githubUrl: string): Promise<RepoInfo> {
  const res = await fetch(`${BASE}/repo/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ github_url: githubUrl }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail ?? 'Ingestion failed');
  }
  return res.json();
}

export async function fetchFileContent(
  sessionId: string,
  filePath: string,
): Promise<{ content: string; language: string; total_lines: number }> {
  const params = new URLSearchParams({ session_id: sessionId, file_path: filePath });
  const res = await fetch(`${BASE}/repo/file?${params}`);
  if (!res.ok) throw new Error('File not found');
  return res.json();
}

export async function* streamChat(
  sessionId: string,
  question: string,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${BASE}/chat/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail ?? 'Chat request failed');
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (raw === '[DONE]') return;
      try {
        yield JSON.parse(raw) as StreamEvent;
      } catch {
        // malformed SSE line — skip
      }
    }
  }
}
