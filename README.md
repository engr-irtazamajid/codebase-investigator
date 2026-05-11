# CodeInvestigator

Ask questions about any public GitHub repo in plain English and get answers grounded in specific files and line ranges — each with an **independent audit** you can actually trust.

---

## Features

- **Grounded answers** — every claim cites `[[file_path:start_line-end_line]]`, rendered as expandable code cards
- **Independent audit** — a separate LLM call with zero access to conversation history checks citation validity, confidence, scope, and contradictions. No self-scoring.
- **Coherent multi-turn conversation** — a server-side claim registry tracks factual assertions across turns so the model can acknowledge or correct prior claims
- **Dual search backend** — vector search (Gemini embeddings) when available, TF-IDF keyword search as a zero-dependency fallback
- **Dual LLM provider** — Gemini primary, OpenRouter automatic fallback on quota exhaustion

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser  (Next.js 16 · TypeScript · Tailwind CSS v4)           │
│                                                                 │
│  RepoInput ──► POST /repo/ingest                                │
│  ChatInterface ──► POST /chat/ask  (SSE stream)                 │
│    ├── Answer tokens   (streamed)                               │
│    ├── CitationCards   (expandable file + line viewer)          │
│    └── AuditPanel      (independent verdict, after stream)      │
└───────────────────────────┬─────────────────────────────────────┘
                            │  HTTP + Server-Sent Events
┌───────────────────────────▼─────────────────────────────────────┐
│  FastAPI backend                                                 │
│                                                                 │
│  POST /repo/ingest                                              │
│    └── clone → chunk → embed (Gemini) or index (TF-IDF)         │
│                                                                 │
│  POST /chat/ask  (EventSourceResponse)                          │
│    ├── search: VectorStore (cosine) or TFIDFStore (keywords)    │
│    ├── LLMClient.stream()  ── Gemini call #1  (history-aware)   │
│    │     streams tokens → parses citations → registers claims   │
│    └── LLMClient.generate() ── Gemini call #2 (no history!)     │
│          independent audit: question + answer + raw chunks      │
│                                                                 │
│  GET  /repo/file  → raw file content for citation viewer        │
└─────────────────────────────────────────────────────────────────┘
```

### SSE event sequence per chat turn

```
data: {"type": "token",     "content": "The auth module..."}   ← streamed live
data: {"type": "token",     "content": " uses JWT..."}
data: {"type": "citations", "data": [...]}                     ← after full answer
data: {"type": "audit",     "data": {...}}                     ← independent call
data: [DONE]
```

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend framework | Next.js 16 (App Router) + TypeScript |
| Styling | Tailwind CSS v4 (no config file needed) |
| Client state | Zustand |
| Icons | lucide-react |
| Backend | FastAPI + uvicorn |
| Streaming | `sse-starlette` (Server-Sent Events) |
| Primary LLM | Gemini (`gemini-2.0-flash-lite`) via `google-generativeai` |
| Fallback LLM | Any OpenRouter model via OpenAI-compatible API (`httpx`) |
| Primary search | Gemini `gemini-embedding-001` → numpy cosine similarity |
| Fallback search | Custom TF-IDF with code-aware tokenizer (pure numpy, zero deps) |
| Session storage | In-memory Python dict (swap to Redis for production) |

---

## Project structure

```
agents-anywhere-assessment/
├── README.md
│
├── backend/
│   ├── .env.example                # copy to .env and fill in keys
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI app + startup validation
│       ├── core/
│       │   ├── config.py           # pydantic-settings (reads .env)
│       │   ├── llm_client.py       # Gemini + OpenRouter unified client
│       │   └── retry.py            # exponential backoff for 429s
│       ├── models/
│       │   └── schemas.py          # single source of truth for all Pydantic models
│       ├── services/
│       │   ├── repo_ingestion.py   # git clone · file walk · line-window chunker
│       │   ├── embedding.py        # Gemini embed_content with async batching
│       │   ├── vector_store.py     # numpy cosine similarity (embedding-based)
│       │   ├── tfidf_store.py      # TF-IDF keyword search (no-Gemini fallback)
│       │   ├── conversation.py     # session store · history · claim registry
│       │   ├── answer.py           # retrieval → stream → citations → claims
│       │   └── audit.py            # independent audit (isolated context)
│       └── api/routes/
│           ├── repo.py             # POST /repo/ingest · GET /repo/file
│           └── chat.py             # POST /chat/ask (SSE)
│
└── frontend/
    └── src/
        ├── app/                    # Next.js App Router
        │   ├── layout.tsx
        │   ├── page.tsx            # landing + chat layout
        │   └── globals.css
        ├── components/
        │   ├── repo/
        │   │   └── RepoInput.tsx   # URL input + ingest trigger
        │   └── chat/
        │       ├── ChatInterface.tsx   # SSE consumer + message orchestration
        │       ├── MessageBubble.tsx   # user / assistant bubble
        │       ├── CitationCard.tsx    # expandable file + line viewer
        │       └── AuditPanel.tsx      # trust score + flag display
        ├── store/
        │   └── conversation.ts     # Zustand store
        ├── lib/
        │   ├── api.ts              # typed API client (all endpoints)
        │   └── utils.ts            # shared helpers + colour utilities
        └── types/
            └── index.ts            # shared domain types
```

---

## Setup

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | 3.12 recommended |
| Node.js 20+ | Required by Next.js 16 |
| `git` in PATH | Used to clone repos at runtime |
| At least one LLM key | See provider table below |

### Provider combinations

| GEMINI_API_KEY | OPENROUTER_API_KEY | Search | Generation |
|---|---|---|---|
| ✓ set | — | Vector (high quality) | Gemini |
| ✓ set | ✓ set | Vector | Gemini → OpenRouter on quota |
| — | ✓ set | TF-IDF keyword | OpenRouter |
| — | — | — | Error at startup |

> **Note:** Embeddings always require `GEMINI_API_KEY`. If only OpenRouter is set, TF-IDF keyword search is used automatically.

---

### 1. Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — see configuration section below
```

**Start the server:**

```bash
uvicorn app.main:app --reload --port 8000
```

On startup you will see confirmation of which providers are active:

```
INFO  ✓ Gemini configured (model: gemini-2.0-flash-lite)
INFO  ✓ OpenRouter configured (model: meta-llama/llama-3.1-8b-instruct:free)
```

API docs available at `http://localhost:8000/docs`

---

### 2. Frontend

```bash
cd frontend

# Copy env file (edit if backend is on a different port)
cp .env.local.example .env.local

# Install dependencies
npm install

# Start dev server
npm run dev
```

Open `http://localhost:3000`

> **Node version:** if `npm run dev` fails, run `nvm use 20` first.

---

## Configuration

All settings live in `backend/.env` (copy from `.env.example`):

### LLM providers

```bash
# ── Gemini (primary) ───────────────────────────────────────────
# Get key: https://aistudio.google.com/app/apikey
# Free tier: ~1500 req/day on gemini-2.0-flash-lite
GEMINI_API_KEY=...

# ── OpenRouter (fallback / alternative) ────────────────────────
# Get key: https://openrouter.ai/keys  (requires verified account)
# Free models need no billing — use the :free suffix
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=...
```

**Recommended free OpenRouter models** (no credit card required):

| Model slug | Notes |
|---|---|
| `meta-llama/llama-3.1-8b-instruct:free` | Fast, good code reasoning |
| `mistralai/mistral-7b-instruct:free` | Lightweight, reliable |
| `deepseek/deepseek-chat:free` | Excellent at code analysis |
| `google/gemini-2.0-flash-lite` | Mirrors Gemini (paid) |

> **OpenRouter 401 errors:** the account must be email-verified before the chat API works. Check your inbox for a verification link at openrouter.ai.

### Search & retrieval

```bash
MODEL_NAME=gemini-2.0-flash-lite       # Gemini generation model
EMBEDDING_MODEL=models/gemini-embedding-001
MAX_RETRIEVAL_CHUNKS=8                 # chunks returned per question
CHUNK_SIZE=60                          # lines per chunk
CHUNK_OVERLAP=15                       # overlap between adjacent chunks
MAX_FILE_SIZE_KB=500                   # files larger than this are skipped
MAX_CHUNKS_PER_REPO=1500               # hard cap per repo
EMBEDDING_BATCH_SIZE=5                 # chunks embedded per API call
```

---

## How the audit works

The audit is the core trust mechanism. It runs in complete isolation from the answer:

```
Answer generation (call #1)        Audit (call #2)
───────────────────────────        ───────────────
Receives:                          Receives:
  • System prompt                    • The question (raw)
  • Retrieved code chunks            • The generated answer
  • Conversation history             • Retrieved code chunks (ground truth)
  • Prior claims digest
  • Current question               Does NOT receive:
                                     • Conversation history
Produces:                            • Prior claims
  • Streamed answer text             • The answer model's reasoning
  • [[file:line-line]] citations
                                   Checks:
                                     1. Citation validity
                                     2. Confidence calibration
                                     3. Scope creep
                                     4. Internal contradiction
                                     5. Missing evidence

                                   Returns:
                                     trust_score (0–10), verdict, flags[]
```

This satisfies the hard requirement that *"self-scoring in the same prompt doesn't count"* — the audit call physically cannot see the answer model's context.

---

## Multi-turn coherence

Each `Session` tracks:

- **Message history** — last 6 turns fed into every answer prompt
- **Claim registry** — cited sentences extracted from each answer and stored as `(turn, claim_text, evidence_file:lines)`

Every new answer prompt receives a **claims digest** (last 10 claims). The model is explicitly instructed to acknowledge prior claims if accurate, or correct them if new evidence contradicts them.

This prevents silent context drop across 8–15 turns of pushback.

---

## Example questions to try

```
How does authentication work here, and what would you change about it?
This signup flow feels off — walk me through it and flag anything risky.
Is there dead code? What's safe to delete?
Why is this function async? Does it need to be?
Suggest a better way to handle errors in the API layer.
Walk me through what this service does. Skip the obvious.
```

---

## Design decisions & trade-offs

### RAG over agentic tool-calling
The spec says the agent "investigates using tools." A fully agentic implementation would have the LLM iteratively decide which files to fetch, discover references, follow call chains, and synthesise across multiple retrieval steps.

We use RAG (retrieve top-k chunks → answer in one shot) instead. Reasons:
- The spec explicitly lists "simple vector search" as the intended stack
- An agentic loop adds latency, error surface, and ~1 day of engineering
- RAG handles the majority of example questions well (retrieval, evaluation, opinion)
- The one case where it falls short — true dead-code detection requiring full call-graph analysis — is an acceptable limitation given the scope

### Audit isolation
The audit call receives only `(question, answer, raw_chunks)` — no conversation history, no prior claims, no system prompt from the answer call. The same model is used but with a completely different context, satisfying the requirement that *"self-scoring in the same prompt doesn't count."*

### In-memory sessions
Sessions live in a Python dict with a 4-hour TTL. Appropriate for a single-instance demo with 8–15 turn conversations. The swap to Redis is one import and a config change — documented in the limitations section.

### TF-IDF fallback
If no `GEMINI_API_KEY` is set, the system falls back to a code-aware TF-IDF store (splits camelCase/snake_case identifiers). Quality is lower but the system stays functional with only an OpenRouter key.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Embedding failed: GEMINI_API_KEY is not set` | Gemini key missing or commented out | Add/uncomment `GEMINI_API_KEY` in `.env` and restart |
| `401 Unauthorized` (OpenRouter) | Account not email-verified, or key revoked | Verify email at openrouter.ai, or regenerate the key |
| `429 quota exceeded` (Gemini) | Free tier daily limit hit | Wait until tomorrow, or set `OPENROUTER_API_KEY` as fallback |
| `No module named 'sse_starlette'` | Running with system Python, not venv | Run `pip install -r requirements.txt` with the correct Python |
| Frontend build fails (Node version) | Node < 20 | Run `nvm use 20` then `npm run dev` |
| `Address already in use` (port 8000) | Stale server process | Run `lsof -ti:8000 \| xargs kill -9` |

---

## CI/CD

### Pipelines

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | Push / PR to `main`, `develop` | Lint · type-check · unit tests (backend) + ESLint · tsc · build (frontend) + Gitleaks secret scan |
| `cd.yml` | Push to `main` or semver tag | Builds backend + frontend Docker images and pushes to GitHub Container Registry (GHCR) |

### Running checks locally

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
ruff check .                  # lint
ruff format --check .         # format
mypy app --ignore-missing-imports
pytest tests/ -v              # 69 unit tests, no API keys needed

# Frontend
cd frontend
npm run lint                  # ESLint
npx tsc --noEmit              # TypeScript
npm run build                 # production build
```

### Pre-commit hooks (optional but recommended)

```bash
pip install pre-commit
pre-commit install
# Now ruff, ruff-format, tsc, and secret detection run on every git commit
```

### Why not Vercel for the backend?

Vercel Serverless Functions have a **60s max execution time** and **no persistent memory between invocations**. Our backend needs both:
- Git clone + embedding during ingestion takes 2–3 minutes
- Sessions (conversation history, vector store) live in-process memory

Use **Railway** (easiest) or **Fly.io** for the backend instead.

### Deploying: Frontend → Vercel, Backend → Railway

**Frontend (Vercel):**
1. Push to GitHub, connect repo at [vercel.com](https://vercel.com)
2. Set one environment variable in the Vercel dashboard:
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-backend.up.railway.app
   ```
3. Every push to `main` deploys automatically — no workflow needed.

**Backend (Railway):**
1. Connect repo at [railway.app](https://railway.app)
2. Railway detects `backend/railway.toml` and uses the Dockerfile automatically
3. Set environment variables in Railway's dashboard:
   ```
   GEMINI_API_KEY=...
   OPENROUTER_API_KEY=...   # optional fallback
   OPENROUTER_MODEL=...
   CORS_ORIGINS=["https://your-vercel-app.vercel.app"]
   ```
4. To enable automatic deploys from the CD pipeline, add `RAILWAY_TOKEN` to GitHub secrets and set the `RAILWAY_ENABLED` repo variable to `true`.

**Local dev with Docker:**
```bash
docker compose up   # backend + frontend with hot-reload
```

---

## Known limitations & production upgrade path

| Limitation | Production fix |
|---|---|
| In-memory sessions lost on restart | Replace `_sessions` dict with Redis + TTL |
| Sequential embedding (slow for large repos) | `asyncio.gather` with semaphore |
| Line-window chunking misses function boundaries | Tree-sitter AST-aware chunker |
| No authentication | API key middleware or OAuth |
| Single process | Already stateless by design — add Redis and scale horizontally |
