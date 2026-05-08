"""cli 모듈: Typer app 및 커맨드 등록."""
from __future__ import annotations

import typer
from typing import Optional

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
    typer.echo("not implemented")


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
    typer.echo("not implemented")


@app.command()
def sync(
    on_conflict: str = typer.Option("skip", "--on-conflict", help="충돌 처리 방식 (skip|force|abort)"),
) -> None:
    """두 GitHub 리포지토리 간 직접 동기화합니다 (Phase 2)."""
    typer.echo("not implemented")
