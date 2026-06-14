"""test_tui.py — Textual TUI key binding tests."""
from __future__ import annotations

from pathlib import Path


def _read_textual_app_source() -> str:
    app_path = Path(__file__).parents[2] / "gitshuttle" / "ui" / "_textual_app.py"
    return app_path.read_text(encoding="utf-8")


def test_tui_binds_a_to_toggle_all():
    """TUI에서 A 키로 전체 선택/해제를 실행해야 한다."""
    source = _read_textual_app_source()

    assert 'Binding("a", "toggle_all"' in source
    assert "def action_toggle_all" in source


def test_tui_binds_e_to_confirm():
    """TUI에서 E 키로 선택을 확정해야 한다."""
    source = _read_textual_app_source()

    assert 'Binding("e", "confirm"' in source
    assert "def action_confirm" in source
