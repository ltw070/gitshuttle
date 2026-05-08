"""config 모듈: gitshuttle.toml 읽기/쓰기 및 대화형 마법사 (스텁)."""
from __future__ import annotations

import sys
from pathlib import Path

# Python 3.10+에서는 tomllib이 표준 라이브러리에 포함됨
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            tomllib = None  # type: ignore[assignment]

DEFAULT_UI = "tui"
CONFIG_FILENAME = "gitshuttle.toml"


def load_config(config_path: Path | None = None) -> dict:
    """gitshuttle.toml을 읽어 dict로 반환한다. 파일이 없으면 기본값을 반환한다."""
    if config_path is None:
        config_path = Path(CONFIG_FILENAME)

    if not config_path.exists():
        return {"export": {"ui": DEFAULT_UI}}

    if tomllib is None:
        return {"export": {"ui": DEFAULT_UI}}

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def get_ui_mode(config_path: Path | None = None) -> str:
    """설정 파일에서 UI 모드를 읽는다. 없으면 기본값(tui)을 반환한다."""
    cfg = load_config(config_path)
    return cfg.get("export", {}).get("ui", DEFAULT_UI)
