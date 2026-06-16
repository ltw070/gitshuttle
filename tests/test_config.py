"""tests/test_config.py — config 모듈 테스트."""
from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# load_config / get_ui_mode
# ---------------------------------------------------------------------------

def test_load_config_default(tmp_path):
    """toml 파일이 없을 때 기본값을 반환해야 한다 (ui='tui')."""
    from gitshuttle.config import load_config

    cfg = load_config(config_path=tmp_path / "nonexistent.toml")
    assert cfg["export"]["ui"] == "tui"


def test_load_config_from_file(tmp_path):
    """[export] ui = 'csv' 로 저장된 toml 파일에서 ui='csv' 를 읽어야 한다."""
    from gitshuttle.config import load_config

    toml_path = tmp_path / "gitshuttle.toml"
    toml_path.write_text('[export]\nui = "csv"\n', encoding="utf-8")

    cfg = load_config(config_path=toml_path)
    assert cfg["export"]["ui"] == "csv"


def test_load_config_all_ui_modes(tmp_path):
    """지원 UI 모드(tui, csv)를 읽을 수 있어야 한다."""
    from gitshuttle.config import load_config

    for mode in ("tui", "csv"):
        toml_path = tmp_path / f"gitshuttle_{mode}.toml"
        toml_path.write_text(f'[export]\nui = "{mode}"\n', encoding="utf-8")
        cfg = load_config(config_path=toml_path)
        assert cfg["export"]["ui"] == mode


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------

def test_save_config(tmp_path):
    """save_config 호출 후 toml 파일이 생성되어야 한다."""
    from gitshuttle.config import save_config

    toml_path = tmp_path / "gitshuttle.toml"
    save_config({"export": {"ui": "csv"}}, config_path=toml_path)

    assert toml_path.exists()


def test_save_config_content(tmp_path):
    """save_config 로 저장한 내용을 load_config 로 다시 읽을 수 있어야 한다."""
    from gitshuttle.config import load_config, save_config

    toml_path = tmp_path / "gitshuttle.toml"
    save_config({"export": {"ui": "csv"}}, config_path=toml_path)

    cfg = load_config(config_path=toml_path)
    assert cfg["export"]["ui"] == "csv"


def test_save_config_encoding_utf8(tmp_path):
    """저장된 toml 파일은 UTF-8 인코딩이어야 한다."""
    from gitshuttle.config import save_config

    toml_path = tmp_path / "gitshuttle.toml"
    save_config({"export": {"ui": "tui"}}, config_path=toml_path)

    # UTF-8 로 읽을 수 있어야 함 (예외 없이)
    content = toml_path.read_text(encoding="utf-8")
    assert "tui" in content


# ---------------------------------------------------------------------------
# get_ui_mode (flag override)
# ---------------------------------------------------------------------------

def test_get_ui_mode_flag_overrides_toml(tmp_path):
    """--ui 플래그가 toml 기본값보다 우선해야 한다."""
    from gitshuttle.config import get_ui_mode

    toml_path = tmp_path / "gitshuttle.toml"
    toml_path.write_text('[export]\nui = "tui"\n', encoding="utf-8")

    result = get_ui_mode(flag="csv", config_path=toml_path)
    assert result == "csv"


def test_get_ui_mode_no_flag_uses_toml(tmp_path):
    """플래그 없을 때 toml 값을 사용해야 한다."""
    from gitshuttle.config import get_ui_mode

    toml_path = tmp_path / "gitshuttle.toml"
    toml_path.write_text('[export]\nui = "csv"\n', encoding="utf-8")

    result = get_ui_mode(flag=None, config_path=toml_path)
    assert result == "csv"


def test_get_ui_mode_default_tui(tmp_path):
    """플래그도 없고 toml도 없으면 기본값 'tui' 를 반환해야 한다."""
    from gitshuttle.config import get_ui_mode

    result = get_ui_mode(flag=None, config_path=tmp_path / "nonexistent.toml")
    assert result == "tui"


def test_get_ui_mode_flag_none_string(tmp_path):
    """flag=None (미지정)은 toml 또는 기본값을 사용해야 한다."""
    from gitshuttle.config import get_ui_mode

    toml_path = tmp_path / "gitshuttle.toml"
    toml_path.write_text('[export]\nui = "csv"\n', encoding="utf-8")

    result = get_ui_mode(flag=None, config_path=toml_path)
    assert result == "csv"
