"""github_auth.py — HTTPS+Token 및 SSH 인증 헬퍼.

토큰은 반환값에만 존재하며 로그·오류 메시지에 절대 출력 금지.
모든 subprocess 호출: encoding='utf-8', env에 PYTHONIOENCODING='utf-8' 포함.
"""
from __future__ import annotations

import re
from pathlib import Path


def build_authenticated_url(url: str, token: str) -> str:
    """HTTPS URL에 토큰을 인라인으로 삽입한다.

    예: https://github.com/org/repo → https://<token>@github.com/org/repo
    토큰은 반환값에만 존재하며 로그에 출력 금지.

    Args:
        url:   HTTPS Git 리포지토리 URL.
        token: Personal Access Token (PAT).

    Returns:
        토큰이 삽입된 인증 URL.
    """
    # https:// 접두사 뒤에 token@를 삽입
    if url.startswith("https://"):
        return "https://" + token + "@" + url[len("https://"):]
    # http:// 도 처리 (비표준이지만 내부 GitLab 등 지원)
    if url.startswith("http://"):
        return "http://" + token + "@" + url[len("http://"):]
    return url


def get_ssh_env(ssh_key_path: Path | str) -> dict:
    """SSH 인증을 위한 GIT_SSH_COMMAND 환경변수 딕셔너리를 반환한다.

    예: {'GIT_SSH_COMMAND': 'ssh -i /path/to/key -o StrictHostKeyChecking=no'}

    Args:
        ssh_key_path: SSH 개인 키 파일 경로.

    Returns:
        GIT_SSH_COMMAND 키를 포함하는 환경변수 딕셔너리.
    """
    key_path = str(ssh_key_path)
    ssh_command = f"ssh -i {key_path} -o StrictHostKeyChecking=no"
    return {"GIT_SSH_COMMAND": ssh_command}


def mask_token_in_url(url: str) -> str:
    """URL에서 토큰 부분을 ***로 마스킹한다 (로그 출력용).

    예: https://<token>@github.com/... → https://***@github.com/...

    Args:
        url: 토큰이 포함될 수 있는 URL.

    Returns:
        토큰이 ***로 마스킹된 URL. 토큰이 없으면 그대로 반환.
    """
    if not url:
        return url
    # https://<anything>@host 패턴에서 <anything> 부분을 ***로 교체
    masked = re.sub(r"(https?://)([^@]+)@", r"\1***@", url)
    return masked
