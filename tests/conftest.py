import subprocess
import pytest
from pathlib import Path


@pytest.fixture
def tmp_git_repo(tmp_path):
    subprocess.run(
        ["git", "init", str(tmp_path)],
        check=True,
        encoding='utf-8',
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        encoding='utf-8',
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        encoding='utf-8',
    )
    (tmp_path / "README.md").write_text("# Test", encoding="utf-8")
    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        check=True,
        encoding='utf-8',
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        encoding='utf-8',
    )
    return tmp_path
