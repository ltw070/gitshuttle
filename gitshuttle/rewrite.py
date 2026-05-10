"""rewrite.py — Import-time rewrite: author mapping, branch isolation, timestamp rewrite.

git fast-export 스트림 텍스트를 라인 단위로 파싱/치환한다.

git fast-export 형식 참고:
  - 작성자 라인: "author Name <email> TIMESTAMP TIMEZONE"
  - committer 라인: "committer Name <email> TIMESTAMP TIMEZONE"
  - branch ref 라인: "commit refs/heads/BRANCH" 또는 "reset refs/heads/BRANCH"

모든 파일 I/O: encoding='utf-8'
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# 정규식 패턴 (컴파일 캐시)
# ---------------------------------------------------------------------------

# "author Name <email> TIMESTAMP TIMEZONE" 또는 "committer ..."
_IDENTITY_RE = re.compile(
    r'^(author|committer)\s+'
    r'(.+?)\s+'           # 이름 (그리디하지 않게)
    r'<([^>]+)>\s+'       # 이메일
    r'(\d+)\s+'           # Unix timestamp
    r'([+-]\d{4})$',      # timezone offset
    re.MULTILINE,
)

# "commit refs/heads/BRANCH" 또는 "reset refs/heads/BRANCH"
_REF_LINE_RE = re.compile(
    r'^(commit|reset)\s+(refs/heads/)(.+)$',
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_author_map(path: str | Path) -> dict:
    """JSON 파일에서 작성자 매핑을 로드한다.

    파일이 없으면 빈 dict를 반환한다.

    JSON 형식 예시:
    {
        "alice@example.com": {"name": "Alice Internal", "email": "alice@corp.com"},
        "bob@example.com":   {"name": "Bob Internal",   "email": "bob@corp.com"}
    }

    Args:
        path: JSON 파일 경로 (str 또는 Path).

    Returns:
        작성자 매핑 dict. 파일 없으면 {}.
    """
    path = Path(path)
    if not path.exists():
        return {}

    with open(path, encoding='utf-8') as f:
        return json.load(f)


def rewrite_authors(
    stream: str,
    author_map: dict,
) -> tuple[str, list[str]]:
    """fast-export 스트림에서 author/committer 이름+이메일을 치환한다.

    매핑 키는 소스 이메일 주소. 값은 {"name": ..., "email": ...} dict.
    미매핑 작성자는 원본 그대로 유지하고 warnings 리스트에 추가된다.

    Args:
        stream:     git fast-export 스트림 텍스트.
        author_map: {"source_email": {"name": "...", "email": "..."}} 형식 매핑.

    Returns:
        (rewritten_stream, warnings) — warnings는 미매핑 작성자 목록.
    """
    warnings: list[str] = []
    unmapped_seen: set[str] = set()

    def _replace(m: re.Match) -> str:
        role = m.group(1)       # "author" or "committer"
        name = m.group(2)       # 원본 이름
        email = m.group(3)      # 원본 이메일
        ts = m.group(4)         # Unix timestamp
        tz = m.group(5)         # timezone offset

        if email in author_map:
            new_name = author_map[email].get("name", name)
            new_email = author_map[email].get("email", email)
        else:
            # 미매핑 → 원본 유지, 경고 수집
            if email not in unmapped_seen:
                unmapped_seen.add(email)
                warnings.append(f"미매핑 작성자: {name} <{email}>")
            return m.group(0)

        return f"{role} {new_name} <{new_email}> {ts} {tz}"

    rewritten = _IDENTITY_RE.sub(_replace, stream)
    return rewritten, warnings


def rewrite_branch_ref(stream: str, target_branch: str) -> str:
    """fast-export 스트림에서 refs/heads/* 를 refs/heads/<target_branch>로 치환한다.

    'commit refs/heads/BRANCH' 와 'reset refs/heads/BRANCH' 라인만 대상.

    Args:
        stream:        git fast-export 스트림 텍스트.
        target_branch: 치환할 대상 브랜치 이름 (예: "imported/main").

    Returns:
        치환된 스트림 텍스트.
    """
    def _replace(m: re.Match) -> str:
        verb = m.group(1)   # "commit" or "reset"
        prefix = m.group(2)  # "refs/heads/"
        return f"{verb} {prefix}{target_branch}"

    return _REF_LINE_RE.sub(_replace, stream)


def rewrite_timestamps(
    stream: str,
    mode: str,
    from_dt: Optional[datetime] = None,
) -> str:
    """fast-export 스트림의 author/committer 타임스탬프를 재작성한다.

    mode:
      "now"      — 모든 커밋의 author/committer date = import 실행 시각 (단일 값)
      "original" — 원본 date 그대로 통과 (변경 없음)
      "from"     — 최초 커밋(가장 오래된 committer timestamp)을 from_dt로 맞추고,
                   이후 커밋은 원본 대비 상대 간격 유지.

    Args:
        stream:  git fast-export 스트림 텍스트.
        mode:    "now" | "original" | "from"
        from_dt: datetime (mode="from" 시 필수). timezone-aware 권장.

    Returns:
        재작성된 스트림 텍스트.

    Raises:
        ValueError: 알 수 없는 mode 또는 mode="from"에서 from_dt가 None인 경우.
    """
    valid_modes = ("now", "original", "from")
    if mode not in valid_modes:
        raise ValueError(f"알 수 없는 mode: {mode!r}. 허용값: {valid_modes}")

    if mode == "original":
        return stream

    if mode == "now":
        now_ts = int(datetime.now(tz=timezone.utc).timestamp())
        return _IDENTITY_RE.sub(
            lambda m: f"{m.group(1)} {m.group(2)} <{m.group(3)}> {now_ts} {m.group(5)}",
            stream,
        )

    # mode == "from"
    if from_dt is None:
        raise ValueError("mode='from' 사용 시 from_dt가 필요합니다.")

    # from_dt를 UTC Unix timestamp로 변환
    if from_dt.tzinfo is None:
        # naive datetime → UTC로 간주
        from_ts = int(from_dt.replace(tzinfo=timezone.utc).timestamp())
    else:
        from_ts = int(from_dt.timestamp())

    # 스트림에서 모든 타임스탬프 추출 → 최솟값(기준점) 파악
    all_timestamps = [int(m.group(4)) for m in _IDENTITY_RE.finditer(stream)]
    if not all_timestamps:
        return stream

    original_base = min(all_timestamps)
    offset = from_ts - original_base

    def _shift(m: re.Match) -> str:
        role = m.group(1)
        name = m.group(2)
        email = m.group(3)
        orig_ts = int(m.group(4))
        tz = m.group(5)
        new_ts = orig_ts + offset
        return f"{role} {name} <{email}> {new_ts} {tz}"

    return _IDENTITY_RE.sub(_shift, stream)


def apply_rewrites(
    stream: str,
    author_map: dict,
    target_branch: str,
    timestamp_mode: str,
    from_dt: Optional[datetime] = None,
) -> tuple[str, list[str]]:
    """author, branch, timestamp 재작성을 순서대로 적용하는 편의 함수.

    순서:
      1. rewrite_authors   (이름/이메일 치환)
      2. rewrite_branch_ref (브랜치 ref 치환)
      3. rewrite_timestamps (타임스탬프 재작성)

    Args:
        stream:         git fast-export 스트림 텍스트.
        author_map:     {"source_email": {"name": ..., "email": ...}} 형식 매핑.
        target_branch:  대상 브랜치 이름.
        timestamp_mode: "now" | "original" | "from"
        from_dt:        mode="from" 시 기준 datetime.

    Returns:
        (rewritten_stream, warnings) — warnings는 미매핑 작성자 경고 목록.
    """
    # 1. author 치환
    stream, warnings = rewrite_authors(stream, author_map)

    # 2. branch ref 치환
    stream = rewrite_branch_ref(stream, target_branch)

    # 3. timestamp 재작성
    stream = rewrite_timestamps(stream, mode=timestamp_mode, from_dt=from_dt)

    return stream, warnings
