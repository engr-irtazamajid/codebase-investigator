"""Tests for repo ingestion: URL normalisation and line-window chunking."""

import pytest

from app.services.repo_ingestion import _chunk_file, normalise_github_url


class TestNormaliseGithubUrl:
    def test_standard_https(self):
        url, name = normalise_github_url("https://github.com/tiangolo/fastapi")
        assert url == "https://github.com/tiangolo/fastapi.git"
        assert name == "fastapi"

    def test_https_with_git_suffix(self):
        url, name = normalise_github_url("https://github.com/tiangolo/fastapi.git")
        assert url == "https://github.com/tiangolo/fastapi.git"
        assert name == "fastapi"

    def test_https_with_trailing_slash(self):
        url, name = normalise_github_url("https://github.com/tiangolo/fastapi/")
        assert url == "https://github.com/tiangolo/fastapi.git"
        assert name == "fastapi"

    def test_ssh_url(self):
        url, name = normalise_github_url("git@github.com:tiangolo/fastapi.git")
        assert url == "https://github.com/tiangolo/fastapi.git"
        assert name == "fastapi"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Not a recognised GitHub URL"):
            normalise_github_url("https://gitlab.com/owner/repo")

    def test_non_url_raises(self):
        with pytest.raises(ValueError):
            normalise_github_url("not-a-url")


class TestChunkFile:
    def test_produces_correct_line_numbers(self, tmp_path):
        f = tmp_path / "test.py"
        lines = [f"line_{i}" for i in range(1, 101)]  # 100 lines
        f.write_text("\n".join(lines))

        chunks = _chunk_file(f, "test.py", "python", chunk_size=20, overlap=5)

        assert chunks[0].start_line == 1
        assert chunks[0].end_line == 20
        # Each chunk covers chunk_size lines
        assert chunks[0].end_line - chunks[0].start_line + 1 == 20

    def test_overlap_between_chunks(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("\n".join([f"line_{i}" for i in range(1, 51)]))

        chunks = _chunk_file(f, "test.py", "python", chunk_size=20, overlap=5)

        # Second chunk should start where first ended minus overlap
        assert chunks[1].start_line == chunks[0].start_line + (20 - 5)

    def test_empty_file_returns_no_chunks(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        chunks = _chunk_file(f, "empty.py", "python", chunk_size=60, overlap=15)
        assert chunks == []

    def test_small_file_produces_single_chunk(self, tmp_path):
        f = tmp_path / "small.py"
        f.write_text("def foo():\n    return 42\n")
        chunks = _chunk_file(f, "small.py", "python", chunk_size=60, overlap=15)
        assert len(chunks) == 1
        assert chunks[0].start_line == 1

    def test_chunk_preserves_content(self, tmp_path):
        f = tmp_path / "code.py"
        content = "import os\nimport sys\nprint('hello')\n"
        f.write_text(content)
        chunks = _chunk_file(f, "code.py", "python", chunk_size=60, overlap=5)
        assert "import os" in chunks[0].content

    def test_language_set_correctly(self, tmp_path):
        f = tmp_path / "code.ts"
        f.write_text("const x: number = 1;\n")
        chunks = _chunk_file(f, "code.ts", "typescript", chunk_size=60, overlap=5)
        assert chunks[0].language == "typescript"
