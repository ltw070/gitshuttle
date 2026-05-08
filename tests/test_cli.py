"""Tests for gitshuttle CLI scaffold (Sprint 0).

RED phase: these tests will fail until implementation is in place.
"""
import pytest
from typer.testing import CliRunner


def test_help_shows_commands():
    """--help 실행 시 export, import, config 커맨드가 표시되어야 한다."""
    from gitshuttle.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert "export" in result.output
    assert "import" in result.output
    assert "config" in result.output


def test_version():
    """--version 실행 시 버전 문자열이 출력되어야 한다."""
    from gitshuttle.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert "0.1.0" in result.output


def test_default_config_tui():
    """gitshuttle.toml 없을 때 config 기본값이 'tui'여야 한다."""
    from gitshuttle.config import DEFAULT_UI

    assert DEFAULT_UI == "tui"


def test_export_stub(tmp_git_repo):
    """export 커맨드가 에러 없이 실행되어야 한다.

    GITSHUTTLE_HEADLESS=1 로 TUI 를 우회하고 tmp_git_repo 에서 실행한다.
    """
    import os
    from gitshuttle.cli import app

    runner = CliRunner()
    # Typer CliRunner 는 env 파라미터를 지원하지 않으므로 환경변수를 직접 패치한다.
    old_val = os.environ.get("GITSHUTTLE_HEADLESS")
    old_cwd = os.getcwd()
    try:
        os.environ["GITSHUTTLE_HEADLESS"] = "1"
        os.chdir(str(tmp_git_repo))
        result = runner.invoke(app, ["export", "--branch", "HEAD"])
    finally:
        if old_val is None:
            os.environ.pop("GITSHUTTLE_HEADLESS", None)
        else:
            os.environ["GITSHUTTLE_HEADLESS"] = old_val
        os.chdir(old_cwd)

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert "export 완료" in result.output


def test_import_stub():
    """import 커맨드는 --file 없이 실행하면 오류 안내 후 exit code 1."""
    from gitshuttle.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["import"])

    assert result.exit_code == 1
    assert "--file" in result.output or "--file" in (result.output + str(result.exception))


def test_config_stub():
    """config 커맨드가 에러 없이 실행되어야 한다 (1 입력 → tui 선택)."""
    from gitshuttle.cli import app

    runner = CliRunner()
    # "1\n" 을 stdin 으로 제공 → TUI 선택
    result = runner.invoke(app, ["config"], input="1\n")

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
