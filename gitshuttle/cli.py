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
    package_format: str
    bundle_scope: str
    auto_select_message: Optional[str] = None


def _resolve_export_cli_options(
    *,
    full_branch: bool,
    recent: Optional[int],
    package_format: str,
    bundle_scope: str,
) -> ExportCliOptions:
    if not full_branch:
        message = f"최근 {recent}개 커밋을 UI 없이 선택했습니다." if recent is not None else None
        return ExportCliOptions(
            commit_limit=recent,
            package_format=package_format,
            bundle_scope=bundle_scope,
            auto_select_message=message,
        )

    if package_format != "bundle":
        raise ValueError("--full-branch 옵션은 --format bundle에서만 사용할 수 있습니다.")
    if recent is not None:
        raise ValueError("--full-branch 옵션은 --recent와 함께 사용할 수 없습니다.")

    return ExportCliOptions(
        commit_limit=1,
        package_format="bundle",
        bundle_scope="full",
        auto_select_message="현재 브랜치 tip 기준 전체 이력을 UI 없이 선택했습니다.",
    )


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
    ui: Optional[str] = typer.Option(None, "--ui", help="UI 모드 (tui|csv|html|prompt)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="출력 경로"),
    package_format: str = typer.Option(
        "bundle",
        "--format",
        help="패키지 형식 (bundle|patchset). patchset은 cherry-pick/replay용입니다.",
    ),
    patchset_compression: str = typer.Option(
        "fast",
        "--patchset-compression",
        help="patchset 압축 방식 (fast|stored|deflated). stored가 가장 빠르지만 파일이 큽니다.",
    ),
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
    from gitshuttle.ui.tui import select_commits_tui
    from gitshuttle.config import get_ui_mode

    repo_path = repo if repo is not None else Path.cwd()
    output_dir = Path(output) if output else repo_path
    branch_name = branch or "HEAD"
    try:
        export_options = _resolve_export_cli_options(
            full_branch=full_branch,
            recent=recent,
            package_format=package_format,
            bundle_scope=bundle_scope,
        )
    except ValueError as e:
        typer.echo(f"[오류] {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"source        : {repo_path}")
    typer.echo(f"커밋 목록을 읽는 중... (브랜치: {branch_name})")
    commits = get_commits(repo_path, branch=branch_name, limit=export_options.commit_limit)

    if not commits:
        typer.echo("커밋이 없습니다.", err=True)
        raise typer.Exit(1)

    typer.echo(f"총 {len(commits)}개 커밋을 찾았습니다.")

    if export_options.auto_select_message is not None:
        selected = commits
        typer.echo(export_options.auto_select_message)
    else:
        selected = None

    # UI 모드 결정: --ui 플래그 > gitshuttle.toml > 기본값(tui)
    config_path = repo_path / "gitshuttle.toml" if repo is not None else None
    ui_mode = get_ui_mode(flag=ui, config_path=config_path)

    if selected is None:
        if ui_mode == "tui":
            selected = select_commits_tui(commits)
        elif ui_mode == "csv":
            from gitshuttle.ui.csv_ui import generate_csv, parse_csv
            csv_path = output_dir / "commits.csv"
            generate_csv(commits, csv_path)
            typer.echo(f"commits.csv 생성: {csv_path}")
            typer.echo("include 컬럼을 Y/N 으로 편집 후 Enter 를 누르세요.")
            input()
            selected = parse_csv(csv_path, commits)
        elif ui_mode == "html":
            from gitshuttle.ui.html_ui import generate_html, parse_selection_json
            html_path = output_dir / "commits.html"
            generate_html(commits, html_path)
            typer.echo(f"HTML 생성: {html_path}")
            typer.echo("브라우저에서 열어 커밋을 선택하고 selection.json 을 다운로드하세요.")
            json_path_str = input("selection.json 경로 입력: ").strip()
            selected = parse_selection_json(json_path_str, commits)
        elif ui_mode == "prompt":
            from gitshuttle.ui.prompt_ui import select_commits_prompt
            selected = select_commits_prompt(commits)
        else:
            typer.echo(f"알 수 없는 UI 모드 '{ui_mode}'. tui 로 대체합니다.")
            selected = select_commits_tui(commits)

    if not selected:
        typer.echo("선택된 커밋이 없습니다. 종료합니다.")
        raise typer.Exit(0)

    typer.echo(f"{len(selected)}개 커밋 선택됨. 패키지를 생성합니다...")

    result = run_export(
        repo_path=repo_path,
        commits=selected,
        output_dir=output_dir,
        branch=branch_name,
        package_format=export_options.package_format,
        patchset_compression=patchset_compression,
        bundle_scope=export_options.bundle_scope,
    )

    label = "patchset" if export_options.package_format == "patchset" else "bundle"
    typer.echo(f"{label:<8}: {result.bundle}")
    typer.echo(f"sha256   : {result.sha256}")
    typer.echo(f"manifest : {result.manifest}")
    typer.echo("export 완료.")


@app.command(name="import")
def import_(
    file: Optional[str] = typer.Option(None, "--file", "-f", help=".bundle 또는 .patchset 파일 경로"),
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
        help="import 대상 브랜치 이름. 미지정 시 'imported/<소스브랜치>'.",
    ),
    timestamp: Optional[str] = typer.Option(
        None,
        "--timestamp",
        help="타임스탬프 재작성 모드 (now|original|from=DATETIME). CLI > toml > 기본값(now).",
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        help="import 방식 (auto|bundle|replay). replay는 patchset을 cherry-pick처럼 적용합니다.",
    ),
) -> None:
    """shuttle 패키지를 대상 리포지토리에 반입합니다."""
    from gitshuttle.import_ import run_import, ChecksumError, ImportConflictError
    from gitshuttle.config import get_import_config

    if not file:
        typer.echo("[오류] --file 옵션이 필요합니다.", err=True)
        raise typer.Exit(1)

    bundle_path = Path(file)
    if not bundle_path.exists():
        typer.echo(f"[오류] 파일을 찾을 수 없습니다: {bundle_path}", err=True)
        raise typer.Exit(1)

    repo_path = repo if repo is not None else Path.cwd()

    # toml 기본값 읽기
    config_path = repo_path / "gitshuttle.toml" if repo is not None else None
    import_cfg = get_import_config(config_path=config_path)

    # CLI 옵션 우선 (CLI > toml > 기본값)
    effective_author_map = author_map if author_map is not None else import_cfg.get("author_map")
    effective_timestamp = timestamp if timestamp is not None else import_cfg.get("timestamp", "now")

    typer.echo(f"bundle        : {bundle_path}")
    typer.echo(f"target        : {repo_path}")
    typer.echo(f"conflict      : {on_conflict}")
    typer.echo(f"mode          : {mode}")
    if target_branch:
        typer.echo(f"target-branch : {target_branch}")
    if effective_author_map:
        typer.echo(f"author-map    : {effective_author_map}")
    typer.echo(f"timestamp     : {effective_timestamp}")
    typer.echo("반입을 시작합니다...")

    def _confirm_duplicate_message(head_subject: str, first_subject: str) -> bool:
        typer.echo(
            "\n[경고] 대상 브랜치의 마지막 커밋 메시지와 "
            "새로 붙일 첫 replay 커밋 메시지가 같습니다.",
            err=True,
        )
        typer.echo(f"  이전 마지막 커밋: {head_subject}", err=True)
        typer.echo(f"  새 replay 커밋   : {first_subject}", err=True)
        return typer.confirm("이대로 계속 진행할까요?", default=False)

    try:
        result = run_import(
            bundle_path=bundle_path,
            repo_path=repo_path,
            on_conflict=on_conflict,
            author_map_path=effective_author_map,
            target_branch=target_branch,
            timestamp_mode=effective_timestamp,
            import_mode=mode,
            confirm_duplicate_message=_confirm_duplicate_message,
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

    # 미매핑 작성자 경고 출력
    if result.warnings:
        typer.echo("\n[경고] 매핑되지 않은 작성자:", err=True)
        for w in result.warnings:
            typer.echo(f"  {w}", err=True)

    typer.echo("\nimport 완료.")
    typer.echo(f"  imported : {result.imported}개")
    typer.echo(f"  skipped  : {result.skipped}개")
    typer.echo(f"  total    : {result.total}개")


@app.command()
def config() -> None:
    """대화형 마법사로 gitshuttle.toml 설정을 변경합니다."""
    from gitshuttle.config import run_config_wizard
    run_config_wizard()


@app.command()
def sync(
    on_conflict: str = typer.Option("skip", "--on-conflict", help="충돌 처리 방식 (skip|force|abort)"),
) -> None:
    """두 GitHub 리포지토리 간 직접 동기화합니다 (Phase 2)."""
    typer.echo(
        "[Phase 2] sync 커맨드는 아직 CLI에서 지원되지 않습니다.\n"
        "Python API로 직접 사용하려면:\n\n"
        "  from gitshuttle.sync_ import run_sync\n"
        "  run_sync(source_url=..., target_url=...,\n"
        "           source_token=..., target_token=...)\n\n"
        "gitshuttle.toml 설정 방법은 README.md의 sync 섹션을 참고하세요."
    )
