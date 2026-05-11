"""Shared fixtures and test environment setup."""
import os

import pytest

# Set env vars before any app imports so pydantic-settings reads them
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("OPENROUTER_API_KEY", "")


from app.services.repo_ingestion import CodeChunk  # noqa: E402


@pytest.fixture
def sample_chunks() -> list[CodeChunk]:
    return [
        CodeChunk(
            id="1",
            file_path="src/auth.py",
            start_line=1,
            end_line=30,
            content=(
                "import jwt\n"
                "def authenticate(token: str) -> dict:\n"
                "    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])\n"
                "    return payload\n"
            ),
            language="python",
        ),
        CodeChunk(
            id="2",
            file_path="src/models.py",
            start_line=1,
            end_line=20,
            content=(
                "class User:\n"
                "    def __init__(self, id: int, email: str):\n"
                "        self.id = id\n"
                "        self.email = email\n"
            ),
            language="python",
        ),
        CodeChunk(
            id="3",
            file_path="src/api.py",
            start_line=1,
            end_line=25,
            content=(
                "from fastapi import FastAPI, HTTPException\n"
                "app = FastAPI()\n"
                "@app.get('/users/{user_id}')\n"
                "async def get_user(user_id: int):\n"
                "    raise HTTPException(status_code=404, detail='Not found')\n"
            ),
            language="python",
        ),
    ]
