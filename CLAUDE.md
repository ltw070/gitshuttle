# CLAUDE.md — GitShuttle

## 프로젝트 목적

망분리(Air-Gapped) 환경에서 외부망 → 내부망으로 Git 히스토리를 USB 등 물리 매체를 통해 이전하는 CLI 도구.
핵심 제약: 인터넷 없음, Windows 환경, Python 없는 환경도 지원(exe).

PRD 전체 내용은 `PRD.md` 참고.

---

## 기술 스택

| 항목 | 결정 사항 |
|------|-----------|
| Language | Python 3.10+ |
| Git 지원 범위 | 2.37 이상 |
| TUI | Textual (우선 검토), 대안: Rich + prompt_toolkit |
| CLI 프레임워크 | Typer 또는 Click |
| 배포 | PyInstaller → `gitshuttle.exe` 단일 파일 |
| 압축 | ZIP 또는 tar.gz |
| 무결성 검증 | SHA-256 |

---

## 엔트리포인트

```
python -m gitshuttle   →   gitshuttle/__main__.py
```

PyInstaller 빌드도 동일 엔트리포인트를 사용한다.

---

## 명령어 구조

```
gitshuttle export   [--branch] [--ui tui|csv|html|prompt] [--output]
gitshuttle import   --file <path> [--on-conflict skip|force|abort]
gitshuttle config   (대화형 마법사 — gitshuttle.toml 수정)
```

---

## UI 모드 (export)

기본값은 `tui`. 우선순위: `--ui 플래그` > `gitshuttle.toml` > 하드코딩 기본값(tui).

| 모드 | 구현 방식 |
|------|-----------|
| `tui` | Textual 체크박스 + 테이블. Shift 범위선택, 작성자/파일/날짜 필터. |
| `csv` | `commits.csv` 생성 → 사용자가 `include` 컬럼 Y/N 편집 → 재입력 |
| `html` | 단일 `.html` 생성(인터넷 불필요) → 브라우저 선택 → `selection.json` → export |
| `prompt` | InquirerPy 방향키 + Space 멀티셀렉트 |

공통: 이미 타겟에 반영된 커밋은 `[imported]` 태그로 표시.

---

## 충돌 처리 (import)

`--on-conflict skip`(기본) / `force` / `abort`

---

## 생성 파일 구조

```
shuttle_YYMMDD.bundle        # git bundle (압축)
shuttle_YYMMDD.sha256        # SHA-256 체크섬
shuttle_YYMMDD_manifest.txt  # 커밋 목록 요약 (반출입 심사용)
```

---

## 개발 로드맵

- **Phase 1**: CLI + TUI (현재 범위)
- **Phase 2**: 데스크탑 GUI (마우스 기반, 히스토리 그래프)

Phase 1 완료 전까지 GUI 관련 코드는 작성하지 않는다.

---

## 주요 제약

- Windows 우선. 터미널 호환성(Windows Terminal, CMD, PowerShell) 모두 검증 필요.
- 망분리 환경이므로 외부 네트워크 호출 코드는 절대 포함하지 않는다.
- `gitshuttle.exe`는 Python 없는 환경에서도 동작해야 한다 — 런타임 의존성을 PyInstaller로 모두 번들.
- 대용량 리포지토리 대응: 분할 압축(Split archive) 지원.
