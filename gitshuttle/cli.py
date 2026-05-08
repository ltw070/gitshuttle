"""cli 모듈: Typer app 및 커맨드 등록."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from gitshuttle import __version__

app = typer.Typer(
    name="gitshuttle",
    help="Air-gapped Git history synchronizer.",
    no_args_is_help=True,
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
    ui: Optional[str] = typer.Option(None, "--ui", help="UI 모드 (tui|csv|html|prompt)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="출력 경로"),
) -> None:
    """선택한 커밋을 .bundle 파일로 추출합니다."""
    from gitshuttle.git_ops import get_commits
    from gitshuttle.export_ import run_export
    from gitshuttle.ui.tui import select_commits_tui
    from gitshuttle.config import get_ui_mode

    repo_path = Path.cwd()
    output_dir = Path(output) if output else repo_path
    branch_name = branch or "HEAD"

    typer.echo(f"커밋 목록을 읽는 중... (브랜치: {branch_name})")
    commits = get_commits(repo_path, branch=branch_name)

    if not commits:
        typer.echo("커밋이 없습니다.", err=True)
        raise typer.Exit(1)

    typer.echo(f"총 {len(commits)}개 커밋을 찾았습니다.")

    # UI 모드 결정: --ui 플래그 > gitshuttle.toml > 기본값(tui)
    ui_mode = get_ui_mode(flag=ui)

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
    )

    typer.echo(f"bundle   : {result.bundle}")
    typer.echo(f"sha256   : {result.sha256}")
    typer.echo(f"manifest : {result.manifest}")
    typer.echo("export 완료.")


@app.command(name="import")
def import_(
    file: Optional[str] = typer.Option(None, "--file", "-f", help=".bundle 파일 경로"),
    on_conflict: str = typer.Option("skip", "--on-conflict", help="충돌 처리 방식 (skip|force|abort)"),
) -> None:
    """shuttle 패키지를 현재 리포지토리에 반입합니다."""
    typer.echo("not implemented")


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
    typer.echo("not implemented")
