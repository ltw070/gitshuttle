"""_textual_app.py — Textual CommitSelectorApp.

이 파일은 tui.py 에서만 import 된다.
Textual 이 설치된 환경에서만 동작한다.
"""
from __future__ import annotations

from gitshuttle.git_ops import Commit

try:
    from textual.app import App, ComposeResult
    from textual.widgets import DataTable, Header, Footer
    from textual.binding import Binding
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False


if _TEXTUAL_AVAILABLE:
    class CommitSelectorApp(App):
        """커밋 선택 TUI 앱.

        사용법:
          - 방향키로 이동
          - Space 로 선택/해제
          - A 로 전체 선택/해제
          - E 또는 Enter 로 확정
          - Q 로 취소
        """

        BINDINGS = [
            Binding("q", "quit", "취소"),
            Binding("a", "toggle_all", "전체 선택/해제"),
            Binding("e", "confirm", "Export"),
            Binding("enter", "confirm", "확정"),
            Binding("space", "toggle_select", "선택"),
        ]

        CSS = """
        DataTable {
            height: 1fr;
        }
        """

        def __init__(
            self,
            commits: list[Commit],
            already_imported: set[str],
        ) -> None:
            super().__init__()
            self._commits = commits
            self._already_imported = already_imported
            self._selected: set[int] = set()
            self._result: list[Commit] = []

        def compose(self) -> ComposeResult:
            yield Header()
            yield DataTable()
            yield Footer()

        def on_mount(self) -> None:
            table = self.query_one(DataTable)
            table.add_columns("", "Hash", "Date", "Author", "Message", "Files")
            for i, commit in enumerate(self._commits):
                tag = " [imported]" if commit.hash in self._already_imported else ""
                table.add_row(
                    "[ ]",
                    commit.short_hash,
                    commit.date[:10],
                    commit.author,
                    commit.message + tag,
                    str(commit.files_changed),
                    key=str(i),
                )

        def action_toggle_select(self) -> None:
            table = self.query_one(DataTable)
            row_key = table.cursor_row
            if row_key in self._selected:
                self._selected.discard(row_key)
                table.update_cell_at((row_key, 0), "[ ]")
            else:
                self._selected.add(row_key)
                table.update_cell_at((row_key, 0), "[x]")

        def action_toggle_all(self) -> None:
            table = self.query_one(DataTable)
            if len(self._selected) == len(self._commits):
                self._selected.clear()
                marker = "[ ]"
            else:
                self._selected = set(range(len(self._commits)))
                marker = "[x]"

            for row_index in range(len(self._commits)):
                table.update_cell_at((row_index, 0), marker)

        def action_confirm(self) -> None:
            self._result = [
                self._commits[i] for i in sorted(self._selected)
            ]
            self.exit(self._result)

        def run_selection(self) -> list[Commit]:
            """동기 실행 후 선택된 커밋 목록을 반환한다."""
            result = self.run()
            if result is None:
                return []
            return result

else:
    class CommitSelectorApp:  # type: ignore[no-redef]
        """Textual 미설치 시 사용되는 폴백 구현."""

        def __init__(self, commits: list[Commit], already_imported: set[str]) -> None:
            self._commits = commits

        def run_selection(self) -> list[Commit]:
            raise RuntimeError(
                "Textual 이 설치되어 있지 않습니다. "
                "'pip install textual' 로 설치하거나 "
                "'--ui csv' 모드를 사용하세요."
            )
