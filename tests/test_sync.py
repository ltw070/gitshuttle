"""test_sync.py — Sprint 7 Direct Sync TDD 테스트.

TDD RED phase: github_auth.py, sync_.py, config.py 확장 전에 작성.
네트워크는 unittest.mock.patch로 모두 mock 처리.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. test_build_authenticated_url
# ---------------------------------------------------------------------------

def test_build_authenticated_url():
    """HTTPS URL에 토큰을 인라인으로 삽입하는 형식을 검증한다."""
    from gitshuttle.github_auth import build_authenticated_url

    url = "https://github.com/org/repo"
    token = "ghp_testtoken123"

    result = build_authenticated_url(url, token)

    # 형식: https://<token>@github.com/org/repo
    assert result == "https://ghp_testtoken123@github.com/org/repo"
    # 원본 URL은 변경되지 않아야 함
    assert url == "https://github.com/org/repo"


def test_build_authenticated_url_with_trailing_slash():
    """URL 끝에 슬래시가 있어도 정상 처리된다."""
    from gitshuttle.github_auth import build_authenticated_url

    url = "https://github.com/org/repo.git"
    token = "mytoken"

    result = build_authenticated_url(url, token)

    assert result.startswith("https://mytoken@github.com/")
    assert "org/repo.git" in result


# ---------------------------------------------------------------------------
# 2. test_get_ssh_env
# ---------------------------------------------------------------------------

def test_get_ssh_env():
    """SSH 인증을 위한 GIT_SSH_COMMAND 환경변수 딕셔너리를 반환한다."""
    from gitshuttle.github_auth import get_ssh_env

    key_path = Path("/home/user/.ssh/id_rsa")
    result = get_ssh_env(key_path)

    assert isinstance(result, dict)
    assert "GIT_SSH_COMMAND" in result
    # 키 파일 경로가 포함되어야 한다
    assert str(key_path) in result["GIT_SSH_COMMAND"]
    # ssh 명령어로 시작해야 한다
    assert result["GIT_SSH_COMMAND"].startswith("ssh ")


def test_get_ssh_env_string_path():
    """문자열 경로도 정상 처리된다."""
    from gitshuttle.github_auth import get_ssh_env

    key_path = "C:/Users/user/.ssh/id_rsa_deploy"
    result = get_ssh_env(key_path)

    assert "GIT_SSH_COMMAND" in result
    assert key_path in result["GIT_SSH_COMMAND"]


# ---------------------------------------------------------------------------
# 3. test_mask_token_in_url
# ---------------------------------------------------------------------------

def test_mask_token_in_url():
    """URL에서 토큰 부분을 ***로 마스킹한다."""
    from gitshuttle.github_auth import mask_token_in_url

    url = "https://ghp_secrettoken@github.com/org/repo"
    result = mask_token_in_url(url)

    assert "ghp_secrettoken" not in result
    assert "***" in result
    assert "github.com/org/repo" in result


# ---------------------------------------------------------------------------
# 4. test_mask_token_empty_url
# ---------------------------------------------------------------------------

def test_mask_token_empty_url():
    """토큰 없는 일반 URL은 그대로 반환한다."""
    from gitshuttle.github_auth import mask_token_in_url

    plain_url = "https://github.com/org/repo"
    result = mask_token_in_url(plain_url)

    # 변경 없이 그대로 반환
    assert result == plain_url


def test_mask_token_in_url_empty_string():
    """빈 문자열은 빈 문자열을 반환한다."""
    from gitshuttle.github_auth import mask_token_in_url

    result = mask_token_in_url("")
    assert result == ""


# ---------------------------------------------------------------------------
# 5. test_get_sync_config_empty
# ---------------------------------------------------------------------------

def test_get_sync_config_empty(tmp_path):
    """config 파일이 없을 때 빈 dict를 반환한다."""
    from gitshuttle.config import get_sync_config

    nonexistent = tmp_path / "no_config.toml"
    result = get_sync_config(config_path=nonexistent)

    assert result == {}


def test_get_sync_config_no_sync_section(tmp_path):
    """[sync] 섹션이 없는 toml 파일은 빈 dict를 반환한다."""
    from gitshuttle.config import get_sync_config

    config_file = tmp_path / "gitshuttle.toml"
    config_file.write_text('[export]\nui = "tui"\n', encoding='utf-8')

    result = get_sync_config(config_path=config_file)
    assert result == {}


# ---------------------------------------------------------------------------
# 6. test_get_sync_config_with_source
# ---------------------------------------------------------------------------

def test_get_sync_config_with_source(tmp_path):
    """[sync.source] 섹션을 읽어 올바른 dict를 반환한다."""
    from gitshuttle.config import get_sync_config

    config_file = tmp_path / "gitshuttle.toml"
    config_file.write_text(
        '[sync]\n'
        '[sync.source]\n'
        'url = "https://github.com/org1/repo"\n'
        'auth = "token"\n'
        '[sync.target]\n'
        'url = "https://github.com/org2/repo"\n'
        'auth = "token"\n',
        encoding='utf-8',
    )

    result = get_sync_config(config_path=config_file)

    assert "source" in result
    assert result["source"]["url"] == "https://github.com/org1/repo"
    assert result["source"]["auth"] == "token"


def test_get_sync_config_with_target(tmp_path):
    """[sync.target] 섹션도 올바르게 파싱한다."""
    from gitshuttle.config import get_sync_config

    config_file = tmp_path / "gitshuttle.toml"
    config_file.write_text(
        '[sync]\n'
        '[sync.target]\n'
        'url = "https://github.com/org2/repo"\n'
        'auth = "ssh"\n',
        encoding='utf-8',
    )

    result = get_sync_config(config_path=config_file)
    assert "target" in result
    assert result["target"]["auth"] == "ssh"


# ---------------------------------------------------------------------------
# 7. test_run_sync_calls_git
# ---------------------------------------------------------------------------

def test_run_sync_calls_git(tmp_path):
    """run_sync가 subprocess.run을 올바른 인자로 호출하는지 검증한다 (mock)."""
    from gitshuttle.sync_ import run_sync

    source_url = "https://github.com/org1/repo"
    target_url = "https://github.com/org2/repo"

    with patch("gitshuttle.sync_.subprocess.run") as mock_run:
        # clone/fetch/push 각 subprocess 호출을 성공으로 mock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        run_sync(
            source_url=source_url,
            target_url=target_url,
            work_dir=tmp_path,
        )

    # subprocess.run이 최소 1회 이상 호출되어야 한다
    assert mock_run.call_count >= 1

    # 모든 호출에 encoding='utf-8' 이 포함되어야 한다
    for c in mock_run.call_args_list:
        kwargs = c.kwargs if c.kwargs else {}
        # positional or keyword
        assert kwargs.get("encoding") == "utf-8", (
            f"subprocess.run 호출에 encoding='utf-8' 없음: {c}"
        )


def test_run_sync_subprocess_env_has_pythonioencoding(tmp_path):
    """subprocess.run 호출 env에 PYTHONIOENCODING='utf-8'가 포함되어야 한다."""
    from gitshuttle.sync_ import run_sync

    with patch("gitshuttle.sync_.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        run_sync(
            source_url="https://github.com/org1/repo",
            target_url="https://github.com/org2/repo",
            work_dir=tmp_path,
        )

    for c in mock_run.call_args_list:
        kwargs = c.kwargs if c.kwargs else {}
        env = kwargs.get("env")
        if env is not None:
            assert env.get("PYTHONIOENCODING") == "utf-8", (
                f"env에 PYTHONIOENCODING='utf-8' 없음: {c}"
            )


# ---------------------------------------------------------------------------
# 8. test_run_sync_token_not_in_error
# ---------------------------------------------------------------------------

def test_run_sync_token_not_in_error(tmp_path):
    """오류 발생 시 토큰이 예외 메시지에 포함되지 않아야 한다."""
    from gitshuttle.sync_ import run_sync

    secret_token = "ghp_VERYSECRETTOKEN999"

    with patch("gitshuttle.sync_.subprocess.run") as mock_run:
        # 첫 번째 호출(clone)에서 실패
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "fatal: repository not found"
        mock_run.return_value = mock_result

        with pytest.raises(Exception) as exc_info:
            run_sync(
                source_url="https://github.com/org/repo",
                target_url="https://github.com/org/repo2",
                source_token=secret_token,
                work_dir=tmp_path,
            )

    error_message = str(exc_info.value)
    # 토큰이 예외 메시지에 절대 포함되어서는 안 된다
    assert secret_token not in error_message, (
        f"토큰이 오류 메시지에 노출됨: {error_message}"
    )


def test_run_sync_target_token_not_in_error(tmp_path):
    """target 토큰도 예외 메시지에 노출되지 않아야 한다."""
    from gitshuttle.sync_ import run_sync

    source_secret = "ghp_SOURCE_SECRET"
    target_secret = "ghp_TARGET_SECRET"

    with patch("gitshuttle.sync_.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "fatal: push failed"
        mock_run.return_value = mock_result

        with pytest.raises(Exception) as exc_info:
            run_sync(
                source_url="https://github.com/org/repo",
                target_url="https://github.com/org/repo2",
                source_token=source_secret,
                target_token=target_secret,
                work_dir=tmp_path,
            )

    error_message = str(exc_info.value)
    assert source_secret not in error_message
    assert target_secret not in error_message


# ---------------------------------------------------------------------------
# 9. test_run_sync_returns_result
# ---------------------------------------------------------------------------

def test_run_sync_returns_result(tmp_path):
    """run_sync가 SyncResult 타입을 반환한다."""
    from gitshuttle.sync_ import run_sync, SyncResult

    with patch("gitshuttle.sync_.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = run_sync(
            source_url="https://github.com/org1/repo",
            target_url="https://github.com/org2/repo",
            work_dir=tmp_path,
        )

    assert isinstance(result, SyncResult)
    # 필드 확인
    assert hasattr(result, "synced")
    assert hasattr(result, "skipped")
    assert hasattr(result, "total")
    # 정수 타입 확인
    assert isinstance(result.synced, int)
    assert isinstance(result.skipped, int)
    assert isinstance(result.total, int)
    # 음수 없음
    assert result.synced >= 0
    assert result.skipped >= 0
    assert result.total >= 0


def test_sync_result_fields():
    """SyncResult 데이터클래스 필드 직접 생성 테스트."""
    from gitshuttle.sync_ import SyncResult

    r = SyncResult(synced=5, skipped=2, total=7)
    assert r.synced == 5
    assert r.skipped == 2
    assert r.total == 7
