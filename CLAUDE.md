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

## 인코딩 (한글 깨짐 방지)

Windows에서 한글 깨짐이 발생하는 지점과 대응:

**Python 코드 전반**
- 모든 파일 I/O에 `encoding='utf-8'` 명시. `open()` 기본값 믿지 않기.
- 엔트리포인트(`__main__.py`) 최상단에 UTF-8 모드 강제:
  ```python
  import sys, io
  sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
  sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
  ```
- 또는 환경변수 `PYTHONUTF8=1` / 실행 플래그 `python -X utf8` 사용.
- PyInstaller 빌드 시 `PYTHONUTF8=1`을 `.spec` 파일의 `env`에 포함.

**git 서브프로세스 호출**
- `subprocess.run([...], encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})` 사용.
- `git log`, `git bundle` 출력 파싱 시 항상 `encoding='utf-8'` 지정.

**매니페스트·CSV·HTML 파일 출력**
- 생성 파일 모두 UTF-8 with BOM 없이(`utf-8`, not `utf-8-sig`) 저장.
- CSV는 Excel 호환을 위해 예외적으로 `utf-8-sig` 사용 가능 (Excel이 BOM으로 인코딩 감지).

**git 설정 (이 저장소에 적용 완료)**
- `core.quotepath false` — 한글 파일명 이스케이프 방지
- `i18n.commitEncoding utf-8` — 커밋 메시지 UTF-8
- `i18n.logOutputEncoding utf-8` — `git log` 출력 UTF-8
- `.gitattributes` — 텍스트 파일 `eol=lf encoding=utf-8` 지정

---

## TDD Harness

**모든 구현은 아래 순서를 반드시 따른다.** 자세한 내용은 `HARNESS.md` 참고.

```
1. SubAgent1 (doc-verify)      — 문서 정합성 검증. FAIL 시 구현 진행 금지.
2. SubAgent2 (ai-action)       — TDD 구현 (RED → GREEN → REFACTOR)
3. SubAgent3 (test-verify)     — pytest 실행          ┐ 병렬 실행
   SubAgent4 (compliance-verify) — 규약 준수 검사     ┘
```

SubAgent 정의 파일 위치: `.claude/agents/`

SubAgent 호출 방법 (Claude Code Agent 툴):
- SA1, SA2: 순차 호출
- SA3 + SA4: **단일 메시지에 두 Agent 동시 호출** (병렬)

---

## 주요 제약

- Windows 우선. 터미널 호환성(Windows Terminal, CMD, PowerShell) 모두 검증 필요.
- 망분리 환경이므로 외부 네트워크 호출 코드는 절대 포함하지 않는다.
- `gitshuttle.exe`는 Python 없는 환경에서도 동작해야 한다 — 런타임 의존성을 PyInstaller로 모두 번들.
- 대용량 리포지토리 대응: 분할 압축(Split archive) 지원.
