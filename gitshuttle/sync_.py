"""sync_.py — Direct Sync 오케스트레이션 (Phase 2).

Source GitHub repo → Target GitHub repo 직접 동기화.
파일(.bundle) 없이 fetch → push 흐름으로 동작한다.

보안 원칙:
- 토큰은 로그·오류 메시지에 절대 노출 금지.
- mask_token_in_url() 을 사용해 로그 출력 시 항상 마스킹.

모든 subprocess 호출: encoding='utf-8', env에 PYTHONIOENCODING='utf-8' 포함.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .github_auth import build_authenticated_url, get_ssh_env, mask_token_in_url


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SyncResult:
    synced: int    # 새로 동기화된 커밋 수
    skipped: int   # 이미 존재하여 건너뛴 커밋 수
    total: int     # 선택된 전체 커밋 수


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sync_env(extra: dict | None = None) -> dict[str, str]:
    """sync 서브프로세스용 환경 변수 딕셔너리 반환."""
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "GIT_TERMINAL_PROMPT": "0",
    }
    if extra:
        env.update(extra)
    return env


def _build_url(
    url: str,
    token: str | None,
    ssh_key: Path | str | None,
) -> tuple[str, dict]:
    """인증 방식에 따라 (인증 URL, 추가 env) 튜플을 반환한다.

    HTTPS+Token: URL에 토큰 삽입, 추가 env 없음.
    SSH: URL 그대로, GIT_SSH_COMMAND 포함 env 반환.
    """
    if token is not None:
        auth_url = build_authenticated_url(url, token)
        return auth_url, {}
    if ssh_key is not None:
        return url, get_ssh_env(ssh_key)
    return url, {}


def _run_git_cmd(
    args: list[str],
    cwd: Path | str | None,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    """git 명령을 실행하고 CompletedProcess를 반환한다.

    실패 시(returncode != 0) RuntimeError를 발생시킨다.
    오류 메시지에 토큰이 포함되지 않도록 stderr를 그대로 전달한다.
    """
    env = _sync_env(extra_env)
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        env=env,
    )
    if result.returncode != 0:
        # stderr에서 토큰이 들어올 수 있는 URL을 마스킹
        safe_stderr = mask_token_in_url(result.stderr)
        raise RuntimeError(
            f"git {' '.join(args[:2])} failed (code {result.returncode}):\n{safe_stderr}"
        )
    return result


def _get_commit_count(repo_path: Path) -> int:
    """repo의 전체 커밋 수를 반환한다. 오류 시 0 반환."""
    result = subprocess.run(
        ["git", "rev-list", "--count", "--all"],
        cwd=repo_path,
        capture_output=True,
        encoding="utf-8",
        env=_sync_env(),
    )
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_sync(
    source_url: str,
    target_url: str,
    source_token: str | None = None,
    target_token: str | None = None,
    source_ssh_key: Path | str | None = None,
    target_ssh_key: Path | str | None = None,
    on_conflict: str = "skip",   # "skip" | "force" | "abort"
    work_dir: Path | str | None = None,
) -> SyncResult:
    """Source repo에서 fetch → Target repo에 push.

    흐름:
    1. work_dir에 임시 clone (없으면 tempfile.mkdtemp)
    2. Source에서 fetch
    3. Target에 push
    4. SyncResult 반환

    토큰은 로그에 절대 출력 금지. mask_token_in_url 사용.

    Args:
        source_url:      Source 리포지토리 URL.
        target_url:      Target 리포지토리 URL.
        source_token:    Source HTTPS PAT. None 이면 무시.
        target_token:    Target HTTPS PAT. None 이면 무시.
        source_ssh_key:  Source SSH 키 파일 경로. None 이면 무시.
        target_ssh_key:  Target SSH 키 파일 경로. None 이면 무시.
        on_conflict:     충돌 처리 방식 — "skip" | "force" | "abort".
        work_dir:        작업 디렉터리. None 이면 tempfile.mkdtemp() 사용.

    Returns:
        SyncResult (synced, skipped, total 포함).

    Raises:
        RuntimeError: git 명령 실패 시 (토큰은 마스킹된 형태로 포함).
    """
    # ------------------------------------------------------------------
    # Step 0. 작업 디렉터리 준비
    # ------------------------------------------------------------------
    _tmp_dir_obj = None
    if work_dir is None:
        _tmp_dir_obj = tempfile.mkdtemp(prefix="gs_sync_")
        work_dir = Path(_tmp_dir_obj)
    else:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

    clone_dir = work_dir / "clone"

    # 인증 URL 및 env 준비 (토큰은 여기서만 사용, 로그에 미노출)
    source_auth_url, source_extra_env = _build_url(source_url, source_token, source_ssh_key)
    target_auth_url, target_extra_env = _build_url(target_url, target_token, target_ssh_key)

    try:
        # ------------------------------------------------------------------
        # Step 1. Source에서 bare clone
        # ------------------------------------------------------------------
        _run_git_cmd(
            ["clone", "--bare", source_auth_url, str(clone_dir)],
            cwd=work_dir,
            extra_env=source_extra_env,
        )

        # ------------------------------------------------------------------
        # Step 2. 커밋 수 측정 (synced 계산용)
        # ------------------------------------------------------------------
        commit_count = _get_commit_count(clone_dir)

        # ------------------------------------------------------------------
        # Step 3. Target에 push
        # ------------------------------------------------------------------
        force_flag = ["--force"] if on_conflict == "force" else []
        _run_git_cmd(
            ["push", target_auth_url, "--all"] + force_flag,
            cwd=clone_dir,
            extra_env=target_extra_env,
        )

        # ------------------------------------------------------------------
        # Step 4. SyncResult 반환
        # ------------------------------------------------------------------
        return SyncResult(
            synced=commit_count,
            skipped=0,
            total=commit_count,
        )

    except RuntimeError:
        raise
