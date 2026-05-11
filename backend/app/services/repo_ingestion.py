"""Clone a public GitHub repo, walk its files, and produce line-delimited chunks."""

from __future__ import annotations

import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

# Extensions worth indexing → language label for syntax highlighting
SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".toml": "toml",
    ".env": "bash",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".graphql": "graphql",
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    "vendor",
    "target",
    ".gradle",
    "bin",
    "obj",
}

# Normalise various GitHub URL forms to https clone URL
_GITHUB_RE = re.compile(
    r"(?:https?://github\.com/|git@github\.com:)"
    r"(?P<owner>[^/]+)/(?P<repo>[^/\s.]+?)(?:\.git)?/?$"
)


@dataclass
class CodeChunk:
    id: str
    file_path: str  # relative to repo root
    start_line: int  # 1-indexed
    end_line: int  # inclusive
    content: str
    language: str

    def format_for_prompt(self) -> str:
        return (
            f"[File: {self.file_path}, Lines: {self.start_line}-{self.end_line}]\n"
            f"```{self.language}\n{self.content}\n```"
        )


@dataclass
class IngestedRepo:
    session_id: str
    repo_name: str
    temp_dir: str
    chunks: list[CodeChunk] = field(default_factory=list)
    files_indexed: int = 0


def normalise_github_url(raw: str) -> tuple[str, str]:
    """Return (clone_https_url, repo_name) or raise ValueError."""
    m = _GITHUB_RE.match(raw.strip())
    if not m:
        raise ValueError(f"Not a recognised GitHub URL: {raw!r}")
    owner, repo = m.group("owner"), m.group("repo")
    return f"https://github.com/{owner}/{repo}.git", repo


def _clone(clone_url: str, dest: str) -> None:
    result = subprocess.run(
        ["git", "clone", "--depth=1", clone_url, dest],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr[:500]}")


def _chunk_file(
    abs_path: Path,
    rel_path: str,
    language: str,
    chunk_size: int,
    overlap: int,
) -> list[CodeChunk]:
    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[CodeChunk] = []
    step = max(1, chunk_size - overlap)
    i = 0
    while i < len(lines):
        end = min(i + chunk_size, len(lines))
        content = "\n".join(lines[i:end])
        if content.strip():
            chunks.append(
                CodeChunk(
                    id=str(uuid.uuid4()),
                    file_path=rel_path,
                    start_line=i + 1,
                    end_line=end,
                    content=content,
                    language=language,
                )
            )
        i += step
        if end == len(lines):
            break
    return chunks


def ingest_repo(github_url: str) -> IngestedRepo:
    clone_url, repo_name = normalise_github_url(github_url)
    temp_dir = tempfile.mkdtemp(prefix="codeinvestigator_")
    _clone(clone_url, temp_dir)

    root = Path(temp_dir)
    all_chunks: list[CodeChunk] = []
    files_indexed = 0
    max_kb = settings.max_file_size_kb * 1024

    for abs_path in root.rglob("*"):
        if not abs_path.is_file():
            continue
        # Skip hidden dirs and known junk directories
        if any(
            part in SKIP_DIRS or part.startswith(".")
            for part in abs_path.relative_to(root).parts[:-1]
        ):
            continue
        if abs_path.suffix not in SUPPORTED_EXTENSIONS:
            continue
        if abs_path.stat().st_size > max_kb:
            continue

        rel_path = str(abs_path.relative_to(root))
        language = SUPPORTED_EXTENSIONS[abs_path.suffix]
        file_chunks = _chunk_file(
            abs_path,
            rel_path,
            language,
            settings.chunk_size,
            settings.chunk_overlap,
        )
        all_chunks.extend(file_chunks)
        if file_chunks:
            files_indexed += 1

        if len(all_chunks) >= settings.max_chunks_per_repo:
            break

    return IngestedRepo(
        session_id=str(uuid.uuid4()),
        repo_name=repo_name,
        temp_dir=temp_dir,
        chunks=all_chunks[: settings.max_chunks_per_repo],
        files_indexed=files_indexed,
    )
