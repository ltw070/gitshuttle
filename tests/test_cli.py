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


def test_export_accepts_repo_option(tmp_path, monkeypatch):
    """export --repo 는 현재 디렉터리 대신 지정한 repo 경로를 사용한다."""
    from gitshuttle.cli import app
    from gitshuttle.export_ import ExportResult
    from gitshuttle.git_ops import Commit
    import gitshuttle.export_ as export_module
    import gitshuttle.git_ops as git_ops_module
    import gitshuttle.ui.tui as tui_module

    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()
    output_dir = tmp_path / "out"
    captured = {}

    fake_commit = Commit(
        hash="a" * 40,
        short_hash="aaaaaaa",
        date="2026-06-10 09:00:00 +0900",
        author="ltw070",
        message="test commit",
        files_changed=1,
    )

    def fake_get_commits(repo_path, branch="HEAD"):
        captured["get_commits_repo"] = repo_path
        captured["branch"] = branch
        return [fake_commit]

    def fake_select_commits(commits):
        return commits

    def fake_run_export(repo_path, commits, output_dir, branch, package_format="bundle"):
        captured["run_export_repo"] = repo_path
        captured["output_dir"] = output_dir
        captured["export_branch"] = branch
        captured["package_format"] = package_format
        return ExportResult(
            bundle=output_dir / "test.bundle",
            sha256=output_dir / "test.bundle.sha256",
            manifest=output_dir / "test_manifest.txt",
        )

    monkeypatch.setattr(git_ops_module, "get_commits", fake_get_commits)
    monkeypatch.setattr(tui_module, "select_commits_tui", fake_select_commits)
    monkeypatch.setattr(export_module, "run_export", fake_run_export)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--repo",
            str(repo_dir),
            "--branch",
            "main",
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["get_commits_repo"] == repo_dir.resolve()
    assert captured["run_export_repo"] == repo_dir.resolve()
    assert captured["branch"] == "main"
    assert captured["output_dir"] == output_dir
    assert captured["package_format"] == "bundle"


def test_export_accepts_patchset_format(tmp_path, monkeypatch):
    """export --format patchset 은 run_export에 patchset 형식을 전달한다."""
    from gitshuttle.cli import app
    from gitshuttle.export_ import ExportResult
    from gitshuttle.git_ops import Commit
    import gitshuttle.export_ as export_module
    import gitshuttle.git_ops as git_ops_module
    import gitshuttle.ui.tui as tui_module

    repo_dir = tmp_path / "source_repo"
    repo_dir.mkdir()
    output_dir = tmp_path / "out"
    captured = {}
    fake_commit = Commit(
        hash="a" * 40,
        short_hash="aaaaaaa",
        date="2026-06-10 09:00:00 +0900",
        author="ltw070",
        message="test commit",
        files_changed=1,
    )

    monkeypatch.setattr(git_ops_module, "get_commits", lambda repo_path, branch="HEAD": [fake_commit])
    monkeypatch.setattr(tui_module, "select_commits_tui", lambda commits: commits)

    def fake_run_export(repo_path, commits, output_dir, branch, package_format="bundle"):
        captured["package_format"] = package_format
        return ExportResult(
            bundle=output_dir / "test.patchset",
            sha256=output_dir / "test.patchset.sha256",
            manifest=output_dir / "test_manifest.txt",
        )

    monkeypatch.setattr(export_module, "run_export", fake_run_export)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "--repo",
            str(repo_dir),
            "--output",
            str(output_dir),
            "--format",
            "patchset",
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["package_format"] == "patchset"
    assert "patchset" in result.output


def test_import_stub():
    """import 커맨드는 --file 없이 실행하면 오류 안내 후 exit code 1."""
    from gitshuttle.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["import"])

    assert result.exit_code == 1
    assert "--file" in result.output or "--file" in (result.output + str(result.exception))


def test_import_accepts_repo_option(tmp_path, monkeypatch):
    """import --repo 는 현재 디렉터리 대신 지정한 target repo 경로를 사용한다."""
    from gitshuttle.cli import app
    import gitshuttle.import_ as import_module

    bundle_path = tmp_path / "test.bundle"
    bundle_path.write_bytes(b"fake bundle")
    repo_dir = tmp_path / "target_repo"
    repo_dir.mkdir()
    captured = {}

    def fake_run_import(
        bundle_path,
        repo_path,
        on_conflict="skip",
        sha256_path=None,
        author_map_path=None,
        target_branch=None,
        timestamp_mode="now",
        import_mode="auto",
        confirm_duplicate_message=None,
    ):
        captured["bundle_path"] = bundle_path
        captured["repo_path"] = repo_path
        captured["on_conflict"] = on_conflict
        captured["timestamp_mode"] = timestamp_mode
        captured["import_mode"] = import_mode
        return import_module.ImportResult(imported=1, skipped=0, total=1)

    monkeypatch.setattr(import_module, "run_import", fake_run_import)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--file",
            str(bundle_path),
            "--repo",
            str(repo_dir),
            "--timestamp",
            "original",
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["bundle_path"] == bundle_path
    assert captured["repo_path"] == repo_dir.resolve()
    assert captured["timestamp_mode"] == "original"
    assert captured["import_mode"] == "auto"


def test_import_accepts_replay_mode(tmp_path, monkeypatch):
    """import --mode replay 는 run_import에 replay 모드를 전달한다."""
    from gitshuttle.cli import app
    import gitshuttle.import_ as import_module

    patchset_path = tmp_path / "test.patchset"
    patchset_path.write_bytes(b"fake patchset")
    repo_dir = tmp_path / "target_repo"
    repo_dir.mkdir()
    captured = {}

    def fake_run_import(
        bundle_path,
        repo_path,
        on_conflict="skip",
        sha256_path=None,
        author_map_path=None,
        target_branch=None,
        timestamp_mode="now",
        import_mode="auto",
        confirm_duplicate_message=None,
    ):
        captured["import_mode"] = import_mode
        captured["has_confirm_callback"] = confirm_duplicate_message is not None
        return import_module.ImportResult(imported=1, skipped=0, total=1)

    monkeypatch.setattr(import_module, "run_import", fake_run_import)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--file",
            str(patchset_path),
            "--repo",
            str(repo_dir),
            "--mode",
            "replay",
        ],
    )

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
    assert captured["import_mode"] == "replay"
    assert captured["has_confirm_callback"] is True


def test_config_stub():
    """config 커맨드가 에러 없이 실행되어야 한다 (1 입력 → tui 선택)."""
    from gitshuttle.cli import app

    runner = CliRunner()
    # "1\n" 을 stdin 으로 제공 → TUI 선택
    result = runner.invoke(app, ["config"], input="1\n")

    assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
