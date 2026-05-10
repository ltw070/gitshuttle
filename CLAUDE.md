# CLAUDE.md — GitShuttle

## 문서 업데이트 규칙 (필수)

주요 작업(기능 추가, 스펙 변경, 설계 결정) 후 **커밋 전** 아래 3개 파일을 반드시 확인하고 업데이트한다.

| 파일 | 업데이트 내용 |
|------|-------------|
| `README.md` | 사용자 대상 명령어·설정·워크플로우 변경 반영 |
| `REPORT.md` | 작업 내용, 설계 결정 이유, 영향받은 파일 기록 |
| `CLAUDE.md` | 기술 스택·패키지 구조·제약 사항 변경 반영 |

추가로 해당하는 경우:
- `PLAN.md` — Sprint 추가/변경 시
- `PRD.md` — 기능 스펙 변경 시

> 3개 파일 업데이트 없이 커밋하지 않는다.

---

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

## 패키지 구조

```
gitshuttle/
├── __init__.py
├── __main__.py       # 엔트리포인트 + UTF-8 강제
├── cli.py            # Typer app, 커맨드 등록
├── git_ops.py        # git 서브프로세스 래퍼 (log, bundle, verify)
├── bundle.py         # bundle 생성/검증
├── checksum.py       # SHA-256 생성/검증
├── manifest.py       # 커밋 목록 요약 파일 생성
├── export_.py        # export 오케스트레이션
├── import_.py        # import 오케스트레이션
├── rewrite.py        # 작성자 매핑 & 브랜치 리네임 (fast-export/fast-import 파이프라인)
├── sync_.py          # direct sync 오케스트레이션 (Phase 2)
├── github_auth.py    # HTTPS+Token / SSH 인증 (Phase 2)
├── config.py         # config 마법사, gitshuttle.toml 읽기/쓰기
└── ui/
    ├── __init__.py
    ├── tui.py        # Textual 체크박스+테이블 (기본값)
    ├── csv_ui.py     # commits.csv 생성/파싱 (utf-8-sig)
    ├── html_ui.py    # self-contained HTML, selection.json 파싱
    └── prompt_ui.py  # InquirerPy 멀티셀렉트

tests/
├── conftest.py       # 임시 git repo 픽스처
├── test_git_ops.py
├── test_bundle.py
├── test_checksum.py
├── test_manifest.py
├── test_export.py
├── test_import.py
├── test_rewrite.py   # 작성자 매핑, 브랜치 리네임, 미매핑 원본 유지 테스트
├── test_config.py
├── test_build.py     # gitshuttle.spec, build.ps1 내용 검증
├── test_sync.py      # Direct Sync + github_auth 테스트 (Phase 2)
└── ui/
    ├── test_csv_ui.py
    ├── test_html_ui.py
    └── test_prompt_ui.py

# 빌드 파일 (프로젝트 루트)
gitshuttle.spec       # PyInstaller 스펙 (onefile, PYTHONUTF8=1)
build.ps1             # Windows PowerShell 빌드 자동화
```

---

## 브랜치 전략

```
main
├── sprint/0-scaffold
├── sprint/1-git-core
├── sprint/2-export-tui
├── sprint/3-ui-config
├── sprint/4-import
├── sprint/5-e2e
├── sprint/6-build
└── sprint/7-direct-sync
```

각 Sprint 브랜치에서 개발 → SA3+SA4 PASS → main merge.

---

## 명령어 구조

```
gitshuttle export   [--branch] [--ui tui|csv|html|prompt] [--output]   # Phase 1
gitshuttle import   --file <path> [--on-conflict skip|force|abort]
                    [--author-map <json>] [--target-branch <name>] [--branch-map <json>]  # Phase 1
gitshuttle config   (대화형 마법사 — gitshuttle.toml 수정)              # Phase 1
gitshuttle sync     [--on-conflict skip|force|abort]                    # Phase 2
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

---

## Claude Code 작업 우선순위

### 로컬 환경 우선 확인
- 새로운 작업을 시작하기 전에 로컬 계정, 로컬 토큰, 로컬 설정을 먼저 확인하세요
- 기본/전역 계정 사용 전에 로컬 자격증명 존재 여부를 확인하세요
- `.mcp.json`, `.env`, `~/.ssh/config`, 프로젝트 설정 파일 등 로컬 설정을 우선적으로 읽으세요
- 로컬 설정이 없을 때만 기본/전역 계정을 사용하세요

---

## GitHub 접근 규칙

### 작업 규모별 방식 선택

#### MCP 사용 (토큰 효율적)
- **작은 파일 변경**: < 5KB 파일 생성/수정
- **단일 파일 변경**: 한 번에 1-2개 파일
- **API 작업**: 리포지토리 생성, PR 생성, 이슈 관리
- 도구:
  - `mcp__github-general__create_repository`: 리포지토리 생성
  - `mcp__github-general__create_or_update_file`: 파일 생성/수정 (< 5KB)
  - `mcp__github-general__create_pull_request`: PR 생성
  - `mcp__github-general__push_files`: 소수 파일 업로드

#### Bash + Git 사용 (토큰 절약)
- **큰 파일 변경**: > 10KB 파일 수정
- **대량 파일 변경**: 3개 이상 파일 동시 변경
- **로컬 완성 후 일괄 푸시**: 복잡한 변경사항
- 방식:
  ```bash
  git add .
  git commit -m "type(scope): 메시지"
  git push origin branch
  ```

### 토큰 절약 이유
- MCP: 전체 파일 내용 전송 (100KB = ~25,000 토큰)
- Bash: diff만 전송 (100KB 변경 = ~500 토큰) ← **50배 절약**
