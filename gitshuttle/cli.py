"""cli 모듈: Typer app 및 커맨드 등록."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer

from gitshuttle import __version__

app = typer.Typer(
    name="gitshuttle",
    help="Air-gapped Git history synchronizer.",
    no_args_is_help=True,
)


@dataclass(frozen=True)
class ExportCliOptions:
    """CLI 입력값을 실제 export 실행 옵션으로 정규화한 값."""

    commit_limit: Optional[int]
    bundle_scope: str
    auto_select_message: Optional[str] = None


@dataclass(frozen=True)
class ExportPaths:
    """export 명령에서 사용하는 경로와 브랜치 값."""

    repo_path: Path
    output_dir: Path
    branch_name: str
    config_path: Optional[Path]


@dataclass(frozen=True)
class ImportCliInputs:
    """import 명령에서 검증·설정이 끝난 입력값."""

    bundle_path: Path
    repo_path: Path
    author_map: Optional[str]
    timestamp: str


def _resolve_export_cli_options(
    *,
    full_branch: bool,
    recent: Optional[int],
    bundle_scope: str,
) -> ExportCliOptions:
    if not full_branch:
        message = f"최근 {recent}개 커밋을 UI 없이 선택했습니다." if recent is not None else None
        return ExportCliOptions(
            commit_limit=recent,
            bundle_scope=bundle_scope,
            auto_select_message=message,
        )

    if recent is not None:
        raise ValueError("--full-branch 옵션은 --recent와 함께 사용할 수 없습니다.")

    return ExportCliOptions(
        commit_limit=1,
        bundle_scope="full",
        auto_select_message="현재 브랜치 tip 기준 전체 이력을 UI 없이 선택했습니다.",
    )


def _resolve_export_paths(
    *,
    repo: Optional[Path],
    output: Optional[str],
    branch: Optional[str],
) -> ExportPaths:
    repo_path = repo if repo is not None else Path.cwd()
    return ExportPaths(
        repo_path=repo_path,
        output_dir=Path(output) if output else repo_path,
        branch_name=branch or "HEAD",
        config_path=repo_path / "gitshuttle.toml" if repo is not None else None,
    )


def _select_export_commits(
    *,
    commits,
    export_options: ExportCliOptions,
    ui: Optional[str],
    paths: ExportPaths,
) -> list:
    if export_options.auto_select_message is not None:
        typer.echo(export_options.auto_select_message)
        return commits

    from gitshuttle.config import get_ui_mode

    ui_mode = get_ui_mode(flag=ui, config_path=paths.config_path)
    return _select_commits_by_ui(ui_mode, commits, paths.output_dir)


def _select_commits_by_ui(ui_mode: str, commits, output_dir: Path) -> list:
    if ui_mode == "tui":
        from gitshuttle.ui.tui import select_commits_tui
        return select_commits_tui(commits)

    if ui_mode == "csv":
        from gitshuttle.ui.csv_ui import generate_csv, parse_csv
        csv_path = output_dir / "commits.csv"
        generate_csv(commits, csv_path)
        typer.echo(f"commits.csv 생성: {csv_path}")
        typer.echo("include 컬럼을 Y/N 으로 편집 후 Enter 를 누르세요.")
        input()
        return parse_csv(csv_path, commits)

    typer.echo(f"알 수 없는 UI 모드 '{ui_mode}'. tui 로 대체합니다.")
    from gitshuttle.ui.tui import select_commits_tui
    return select_commits_tui(commits)


def _print_export_result(result) -> None:
    typer.echo(f"{'bundle':<8}: {result.bundle}")
    typer.echo(f"sha256   : {result.sha256}")
    typer.echo(f"manifest : {result.manifest}")
    typer.echo("export 완료.")


def _resolve_import_cli_inputs(
    *,
    file: Optional[str],
    repo: Optional[Path],
    author_map: Optional[str],
    timestamp: Optional[str],
) -> ImportCliInputs:
    if not file:
        typer.echo("[오류] --file 옵션이 필요합니다.", err=True)
        raise typer.Exit(1)

    bundle_path = Path(file)
    if not bundle_path.exists():
        typer.echo(f"[오류] 파일을 찾을 수 없습니다: {bundle_path}", err=True)
        raise typer.Exit(1)

    repo_path = repo if repo is not None else Path.cwd()

    from gitshuttle.config import get_import_config

    import_cfg = get_import_config(
        config_path=repo_path / "gitshuttle.toml" if repo is not None else None
    )
    return ImportCliInputs(
        bundle_path=bundle_path,
        repo_path=repo_path,
        author_map=author_map if author_map is not None else import_cfg.get("author_map"),
        timestamp=timestamp if timestamp is not None else import_cfg.get("timestamp", "now"),
    )


def _print_import_start(
    *,
    inputs: ImportCliInputs,
    on_conflict: str,
    target_branch: Optional[str],
) -> None:
    typer.echo(f"bundle        : {inputs.bundle_path}")
    typer.echo(f"target        : {inputs.repo_path}")
    typer.echo(f"conflict      : {on_conflict}")
    if target_branch:
        typer.echo(f"target-branch : {target_branch}")
    if inputs.author_map:
        typer.echo(f"author-map    : {inputs.author_map}")
    typer.echo(f"timestamp     : {inputs.timestamp}")
    typer.echo("반입을 시작합니다...")


def _print_import_result(result) -> None:
    if result.warnings:
        typer.echo("\n[경고] 매핑되지 않은 작성자:", err=True)
        for warning in result.warnings:
            typer.echo(f"  {warning}", err=True)

    typer.echo("\nimport 완료.")
    typer.echo(f"  imported : {result.imported}개")
    typer.echo(f"  skipped  : {result.skipped}개")
    typer.echo(f"  total    : {result.total}개")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"gitshuttle version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="버전을 출력하고 종료합니다.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """GitShuttle: 망분리 환경을 위한 Git 히스토리 동기화 도구."""


@app.command()
def export(
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="추출할 브랜치"),
    repo: Optional[Path] = typer.Option(
        None,
        "--repo",
        "-r",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="원본 Git 리포지토리 경로 (기본값: 현재 디렉터리)",
    ),
    ui: Optional[str] = typer.Option(None, "--ui", help="UI 모드 (tui|csv)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="출력 경로"),
    bundle_scope: str = typer.Option(
        "range",
        "--bundle-scope",
        help="bundle 범위 방식 (range|full). full은 선택 tip까지 전체 이력을 포함합니다.",
    ),
    full_branch: bool = typer.Option(
        False,
        "--full-branch",
        help="현재/지정 브랜치 tip 기준 전체 이력을 TUI 없이 bundle로 추출합니다.",
    ),
    recent: Optional[int] = typer.Option(
        None,
        "--recent",
        min=1,
        help="UI 없이 최신 N개 커밋을 바로 선택합니다.",
    ),
) -> None:
    """선택한 커밋을 shuttle 패키지로 추출합니다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.export_ import run_export

    paths = _resolve_export_paths(repo=repo, output=output, branch=branch)
    try:
        export_options = _resolve_export_cli_options(
            full_branch=full_branch,
            recent=recent,
            bundle_scope=bundle_scope,
        )
    except ValueError as e:
        typer.echo(f"[오류] {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"source        : {paths.repo_path}")
    typer.echo(f"커밋 목록을 읽는 중... (브랜치: {paths.branch_name})")
    commits = get_commits(
        paths.repo_path,
        branch=paths.branch_name,
        limit=export_options.commit_limit,
    )

    if not commits:
        typer.echo("커밋이 없습니다.", err=True)
        raise typer.Exit(1)

    typer.echo(f"총 {len(commits)}개 커밋을 찾았습니다.")
    selected = _select_export_commits(
        commits=commits,
        export_options=export_options,
        ui=ui,
        paths=paths,
    )

    if not selected:
        typer.echo("선택된 커밋이 없습니다. 종료합니다.")
        raise typer.Exit(0)

    typer.echo(f"{len(selected)}개 커밋 선택됨. 패키지를 생성합니다...")

    result = run_export(
        repo_path=paths.repo_path,
        commits=selected,
        output_dir=paths.output_dir,
        branch=paths.branch_name,
        bundle_scope=export_options.bundle_scope,
    )

    _print_export_result(result)


@app.command(name="import")
def import_(
    file: Optional[str] = typer.Option(None, "--file", "-f", help=".bundle 파일 경로"),
    repo: Optional[Path] = typer.Option(
        None,
        "--repo",
        "-r",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="대상 Git 리포지토리 경로 (기본값: 현재 디렉터리)",
    ),
    on_conflict: str = typer.Option("skip", "--on-conflict", help="충돌 처리 방식 (skip|force|abort)"),
    author_map: Optional[str] = typer.Option(
        None,
        "--author-map",
        help="작성자 매핑 JSON 파일 경로. CLI > toml > 기본값(없음).",
    ),
    target_branch: Optional[str] = typer.Option(
        None,
        "--target-branch",
        help=(
            "rewrite import 대상 브랜치 이름. 미지정 시 rewrite import는 "
            "'imported/<소스브랜치>', 일반 import는 현재 브랜치에 merge."
        ),
    ),
    timestamp: Optional[str] = typer.Option(
        None,
        "--timestamp",
        help="타임스탬프 재작성 모드 (now|original|from=DATETIME). CLI > toml > 기본값(now).",
    ),
) -> None:
    """shuttle 패키지를 대상 리포지토리에 반입합니다."""
    from gitshuttle.import_ import run_import, ChecksumError, ImportConflictError

    inputs = _resolve_import_cli_inputs(
        file=file,
        repo=repo,
        author_map=author_map,
        timestamp=timestamp,
    )
    _print_import_start(
        inputs=inputs,
        on_conflict=on_conflict,
        target_branch=target_branch,
    )

    try:
        result = run_import(
            bundle_path=inputs.bundle_path,
            repo_path=inputs.repo_path,
            on_conflict=on_conflict,
            author_map_path=inputs.author_map,
            target_branch=target_branch,
            timestamp_mode=inputs.timestamp,
        )
    except ChecksumError as e:
        typer.echo(f"\n[오류] {e}", err=True)
        raise typer.Exit(1)
    except ImportConflictError as e:
        typer.echo(f"\n[중단] {e}", err=True)
        raise typer.Exit(1)
    except (FileNotFoundError, ValueError) as e:
        typer.echo(f"\n[오류] {e}", err=True)
        raise typer.Exit(1)

    _print_import_result(result)


@app.command()
def config() -> None:
    """대화형 마법사로 gitshuttle.toml 설정을 변경합니다."""
    from gitshuttle.config import run_config_wizard
    run_config_wizard()
