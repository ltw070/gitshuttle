"""config 모듈: gitshuttle.toml 읽기/쓰기 및 대화형 마법사."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Python 3.11+에서는 tomllib이 표준 라이브러리에 포함됨
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

_VALID_UI_MODES = ("tui", "csv")


def load_config(config_path: Optional[Path] = None) -> dict:
    """gitshuttle.toml을 읽어 dict로 반환한다. 파일이 없으면 기본값을 반환한다."""
    if config_path is None:
        config_path = Path(CONFIG_FILENAME)

    if not config_path.exists():
        return {"export": {"ui": DEFAULT_UI}}

    if tomllib is None:
        # tomllib/tomli 없는 환경: 수동 파싱 (단순 [export] 섹션만 지원)
        return _parse_simple_toml(config_path)

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def save_config(data: dict, config_path: Optional[Path] = None) -> Path:
    """gitshuttle.toml 에 설정을 저장한다.

    tomli_w 미설치 환경을 대비해 수동 toml 직렬화를 사용한다.
    [export] 섹션만 지원 (Phase 1 범위).

    Args:
        data:        저장할 설정 dict. 예: {"export": {"ui": "csv"}}
        config_path: 저장 경로. None 이면 현재 디렉터리의 gitshuttle.toml.

    Returns:
        저장된 파일 경로.
    """
    if config_path is None:
        config_path = Path(CONFIG_FILENAME)

    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        if isinstance(values, dict):
            for key, val in values.items():
                if isinstance(val, str):
                    lines.append(f'{key} = "{val}"')
                elif isinstance(val, bool):
                    lines.append(f"{key} = {str(val).lower()}")
                else:
                    lines.append(f"{key} = {val}")
        lines.append("")  # 섹션 구분 빈 줄

    content = "\n".join(lines)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)

    return config_path


def get_ui_mode(
    flag: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> str:
    """UI 모드를 결정한다.

    우선순위: --ui 플래그 > gitshuttle.toml > 기본값(tui)

    Args:
        flag:        --ui 플래그 값. None 이면 무시.
        config_path: toml 파일 경로. None 이면 기본 경로.

    Returns:
        결정된 UI 모드 문자열.
    """
    if flag is not None:
        return flag

    cfg = load_config(config_path)
    return cfg.get("export", {}).get("ui", DEFAULT_UI)


def run_config_wizard(config_path: Optional[Path] = None) -> None:
    """대화형 마법사로 UI 기본값을 설정한다.

    선택 결과는 gitshuttle.toml 에 저장된다.
    """
    if config_path is None:
        config_path = Path(CONFIG_FILENAME)

    current_mode = get_ui_mode(config_path=config_path)

    menu = {
        "1": "tui",
        "2": "csv",
    }
    labels = {
        "tui": "TUI      — 터미널 인터랙티브",
        "csv": "CSV      — Excel 편집",
    }

    print("\n커밋 선택 UI 기본값을 선택하세요:")
    for num, mode in menu.items():
        current_mark = " ← 현재 설정" if mode == current_mode else ""
        print(f"  [{num}] {labels[mode]}{current_mark}")

    try:
        choice = input("\n선택 (1~4): ").strip()
    except EOFError:
        print("\n입력이 없어 변경하지 않습니다.")
        return

    if choice not in menu:
        print("올바른 선택이 아닙니다. 변경하지 않습니다.")
        return

    selected_mode = menu[choice]
    save_config({"export": {"ui": selected_mode}}, config_path=config_path)
    print(f"설정 저장 완료: ui = {selected_mode}")


def get_import_config(config_path: Path | str | None = None) -> dict:
    """gitshuttle.toml의 [import] 섹션을 읽어 반환한다.

    반환값 예시:
    {
        'author_map': 'map.json',   # 파일 경로 문자열 또는 None
        'timestamp':  'now',        # "now" | "original" | "from=..."
    }

    파일 없거나 [import] 섹션 없으면 기본값 반환:
    {
        'author_map': None,
        'timestamp':  'now',
    }

    Args:
        config_path: toml 파일 경로. None 이면 기본 경로(gitshuttle.toml).

    Returns:
        [import] 섹션 설정 dict.
    """
    defaults: dict = {"author_map": None, "timestamp": "now"}

    if config_path is None:
        config_path = Path(CONFIG_FILENAME)

    config_path = Path(config_path)
    if not config_path.exists():
        return defaults

    cfg = _parse_toml(config_path)
    import_section = cfg.get("import", {})

    result = dict(defaults)
    if "author_map" in import_section:
        result["author_map"] = import_section["author_map"] or None
    if "timestamp" in import_section:
        result["timestamp"] = import_section["timestamp"]

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_simple_toml(config_path: Path) -> dict:
    """tomllib 없는 환경용 단순 toml 파서.

    [export] 섹션의 key = "value" 형태만 지원한다.
    """
    result: dict = {}
    current_section: Optional[str] = None

    with open(config_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                result[current_section] = {}
            elif "=" in line and current_section is not None:
                key, _, raw_val = line.partition("=")
                key = key.strip()
                raw_val = raw_val.strip()
                # 문자열 값 (따옴표 제거)
                if (raw_val.startswith('"') and raw_val.endswith('"')) or \
                   (raw_val.startswith("'") and raw_val.endswith("'")):
                    raw_val = raw_val[1:-1]
                result[current_section][key] = raw_val

    if not result:
        return {"export": {"ui": DEFAULT_UI}}
    return result


def _parse_toml(config_path: Path) -> dict:
    """tomllib 없는 환경용 단순 TOML 파서.

    [import], [export] 같은 일반 섹션과 점(.) 구분 중첩 섹션을 지원한다.
    tomllib이 있으면 그것을 사용하고, 없으면 수동 파싱한다.
    """
    if tomllib is not None:
        try:
            with open(config_path, "rb") as f:
                raw = tomllib.load(f)
            return raw
        except Exception:
            pass

    # 수동 파싱 (중첩 섹션 지원)
    result: dict = {}

    with open(config_path, encoding="utf-8") as f:
        lines = f.readlines()

    current_keys: list[str] = []  # 현재 섹션 키 경로

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            current_keys = [k.strip() for k in section.split(".")]
            # 섹션 경로에 dict 생성
            node = result
            for key in current_keys:
                if key not in node:
                    node[key] = {}
                node = node[key]

        elif "=" in line and current_keys:
            key, _, raw_val = line.partition("=")
            key = key.strip()
            raw_val = raw_val.strip()
            # 문자열 값 (따옴표 제거)
            if (raw_val.startswith('"') and raw_val.endswith('"')) or \
               (raw_val.startswith("'") and raw_val.endswith("'")):
                raw_val = raw_val[1:-1]
            # 현재 섹션 노드에 값 설정
            node = result
            for k in current_keys:
                node = node[k]
            node[key] = raw_val

    return result
