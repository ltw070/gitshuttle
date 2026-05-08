# REPORT.md — GitShuttle 작업 기록

---

## Sprint 진척 현황

| Sprint | 브랜치 | 내용 | 상태 | SA1 | SA2 | SA3 | SA4 |
|--------|--------|------|------|-----|-----|-----|-----|
| 0 | `sprint/0-scaffold` | 프로젝트 기반 구조 | ✅ DONE | PASS | PASS | PASS (6/6) | PASS |
| 1 | `sprint/1-git-core` | Git 핵심 레이어 | ✅ DONE | PASS | PASS | PASS (27/27) | PASS |
| 2 | `sprint/2-export-tui` | Export + TUI | ✅ DONE | PASS | PASS | PASS (39/39) | PASS |
| 3 | `sprint/3-ui-config` | UI 모드 + Config | ⬜ TODO | — | — | — | — |
| 4 | `sprint/4-import` | Import | ⬜ TODO | — | — | — | — |
| 5 | `sprint/5-e2e` | 대용량 + E2E | ⬜ TODO | — | — | — | — |
| 6 | `sprint/6-build` | PyInstaller 빌드 | ⬜ TODO | — | — | — | — |
| 7 | `sprint/7-direct-sync` | Direct Sync (Phase 2) | ⬜ TODO | — | — | — | — |

---

## 2026-05-08

### 1. PRD 작성
- `PRD.md` 초안 작성 (프로젝트 개요, 목표, 핵심 기능, 사용자 시나리오)
- 보완 항목 식별 및 반영:
  - 비기능 요건 추가 (Windows, Git 2.37+, Python 3.10+)
  - 충돌 처리 3단계 옵션 (`skip` / `force` / `abort`)
  - 암호화 요건 제거
  - 손상 파일 복구 방식 정의 (SHA-256 불일치 → 재export 안내)

### 2. 커밋 선택 UI 방식 설계
- A~D 4가지 방식 비교 테이블 작성:
  - **A. TUI (Textual)** — 기본값
  - **B. CSV 편집** — Excel 친화적
  - **C. Self-contained HTML** — 브라우저 선택 → selection.json
  - **D. InquirerPy** — 방향키 + Space
- UI 방식 선택 메커니즘 확정:
  - 설정 파일 `gitshuttle.toml` + `--ui` 플래그 + `gitshuttle config` 마법사 조합

### 3. 배포 방식 결정
- 주 배포: `gitshuttle.exe` (PyInstaller, Python 불필요)
- 보조 실행: `python -m gitshuttle`
- 엔트리포인트: `gitshuttle/__main__.py`

### 4. 개발 로드맵 확정
- Phase 1: CLI + TUI
- Phase 2: 데스크탑 GUI

### 5. 문서 생성
- `README.md`: 사용자 대상 — 설치, 명령어, 워크플로우, 설정
- `CLAUDE.md`: Claude Code 대상 — 기술 스택, 엔트리포인트, 제약 사항

### 6. Git 저장소 초기화 및 GitHub 연결
- 로컬 git init, main 브랜치 설정
- 인코딩 설정:
  - `git config core.quotepath false`
  - `git config i18n.commitEncoding utf-8`
  - `git config i18n.logOutputEncoding utf-8`
  - `.gitattributes` 생성 (UTF-8 + LF)
- GitHub private repo 생성: `https://github.com/ltw070/gitshuttle`
- remote 연결 및 push 완료

### 7. TDD Harness 설계 및 구현
- `.claude/agents/` 에 4개 SubAgent 정의 파일 생성:

  | 파일 | 역할 | 실행 순서 |
  |------|------|-----------|
  | `subagent1-doc-verify.md` | PRD↔README↔CLAUDE.md 정합성 검증 (6개 항목) | 1번 (단독) |
  | `subagent2-ai-action.md` | TDD 구현 (RED→GREEN→REFACTOR) | 2번 (단독) |
  | `subagent3-test-verify.md` | pytest + 커버리지 + 회귀 검사 | 3번 (SA4와 병렬) |
  | `subagent4-compliance-verify.md` | 인코딩·네트워크·Phase범위·PEP8 검사 | 3번 (SA3와 병렬) |

- `HARNESS.md` 생성: 오케스트레이션 흐름 전체 문서화

---

### 8. TDD 개발 계획 수립
- `PLAN.md` 생성: Phase 1을 Sprint 0~6으로 분리, 각 Sprint에 SA 호출 프롬프트 포함
- `CLAUDE.md` 업데이트: 패키지 구조 목표, 브랜치 전략 추가
- 브랜치 전략: `sprint/0-scaffold` ~ `sprint/6-build` → `main` merge

### 9. GitHub MCP 스킬 및 보안 설정
- `.claude/commands/github-mcp-setup.md` 생성: `/github-mcp-setup` 스킬 — 토큰 입력 → `.mcp.json` 자동 생성
- `.mcp.json.example` 생성: 토큰 없는 참고용 템플릿
- `.mcp.json` 초기 양식(플레이스홀더) 커밋 후 `.gitignore` 등록 및 추적 해제
- `.gitignore` 생성: `.mcp.json`, Python, PyInstaller, IDE 패턴 포함

---

### 10. Direct Sync 기능 추가 (Phase 2)
- **배경:** 단일 망 환경에서 두 GitHub repo 간 파일 없이 직접 동기화 요구
- **PRD 3.6** 신규 추가: Direct Sync 스펙, 인증 방식(HTTPS+Token / SSH), `gitshuttle.toml` 설정 구조
- **PRD 시나리오 B** 추가: `gitshuttle sync` 워크플로우
- **PLAN Sprint 7** 추가: `github_auth.py`, `sync_.py`, 환경변수 인증(`GS_SOURCE_TOKEN` / `GS_TARGET_TOKEN`)
- **README** 업데이트: `sync` 명령어 레퍼런스, HTTPS Token / SSH 설정 예시
- **CLAUDE.md** 업데이트: 명령어 구조에 `sync` 추가, 패키지 구조에 `sync_.py` / `github_auth.py` 추가

주요 설계 결정:
- Source / Target 각각 별도 인증 (다른 계정/조직 지원)
- 토큰은 파일에 저장 금지 → 환경변수(`GS_SOURCE_TOKEN`, `GS_TARGET_TOKEN`)로만 주입
- export/import와 동일한 커밋 선택 UI 재사용 (코드 중복 없음)

---

### 11. 문서 업데이트 규칙 수립
- `CLAUDE.md` 최상단에 **문서 업데이트 규칙** 섹션 추가
- 주요 작업 후 커밋 전 README / REPORT / CLAUDE 3개 파일 업데이트 의무화
- 배경: Direct Sync 작업 시 REPORT.md 누락 사례 발생 → 재발 방지

---

## 최종 저장소 현황 (2026-05-08 기준)

```
gitshuttle/
├── .claude/
│   ├── agents/
│   │   ├── subagent1-doc-verify.md
│   │   ├── subagent2-ai-action.md
│   │   ├── subagent3-test-verify.md
│   │   └── subagent4-compliance-verify.md
│   └── commands/
│       └── github-mcp-setup.md
├── .gitattributes
├── .gitignore
├── .mcp.json             ← 로컬 전용 (gitignore)
├── .mcp.json.example
├── CLAUDE.md
├── HARNESS.md
├── PLAN.md
├── PRD.md
├── README.md
└── REPORT.md
```

GitHub: https://github.com/ltw070/gitshuttle (private)

---

---

## Sprint 0 — 프로젝트 기반 구조 (2026-05-08)

**브랜치:** `sprint/0-scaffold` → `main` merge

### 생성 파일
| 파일 | 내용 |
|------|------|
| `pyproject.toml` | Python 3.10+, typer/textual/InquirerPy 의존성, 빌드 설정 |
| `requirements.txt` | 런타임 의존성 |
| `requirements-dev.txt` | pytest, pytest-cov |
| `gitshuttle/__init__.py` | 버전 `0.1.0` 정의 |
| `gitshuttle/__main__.py` | 엔트리포인트, stdout/stderr UTF-8 강제 래핑 |
| `gitshuttle/cli.py` | Typer app, export/import/config/sync 커맨드 스텁 |
| `gitshuttle/config.py` | `load_config()`, `get_ui_mode()`, 기본값 `tui` |
| `tests/__init__.py` | 테스트 패키지 초기화 |
| `tests/conftest.py` | `tmp_git_repo` 픽스처 |
| `tests/test_cli.py` | CLI 테스트 6개 |
| `gitshuttle.toml` | 기본 설정 템플릿 (`[export] ui = "tui"`) |

### 설계 결정
- `import` 예약어 충돌 방지: CLI 커맨드 함수명을 `import_()` 로 정의, `name="import"` 로 등록
- `tomllib` (Python 3.11+ 표준) / `tomli` (3.10 fallback) 분기 처리
- `config.py`에 `DEFAULT_UI = "tui"` 상수 정의 — `gitshuttle.toml` 없을 때 기본값 보장

### TDD Harness 결과
- SA1 (문서 정합성): **PASS** — PRD/README/CLAUDE.md 6개 항목 전부 일치
- SA2 (구현): **PASS** — 6/6 테스트 GREEN
- SA3 (테스트 검증): **PASS** — 6 passed, 커버리지 56% (스캐폴딩 단계 허용 범위)
- SA4 (규약 준수): **PASS** — 인코딩·네트워크·Phase 범위·예약어 전 항목 통과

### 수락 기준 달성
- [x] `python -m gitshuttle --help` → export/import/config/sync 커맨드 목록 출력
- [x] `pytest tests/` → 6 passed, 0 errors
- [x] `gitshuttle.toml` 없을 때 기본값 `tui` 동작

---

## Sprint 1 — Git 핵심 레이어 (2026-05-08)

**브랜치:** `sprint/1-git-core` → `main` merge

### 생성 파일
| 파일 | 내용 |
|------|------|
| `gitshuttle/git_ops.py` | `run_git`, `check_git_version`, `get_commits`, `Commit` 데이터클래스 |
| `gitshuttle/bundle.py` | `create_bundle`, `verify_bundle` |
| `gitshuttle/checksum.py` | `generate`, `verify` (SHA-256) |
| `tests/test_git_ops.py` | 6개 테스트 |
| `tests/test_bundle.py` | 7개 테스트 |
| `tests/test_checksum.py` | 8개 테스트 |

### 설계 결정
- `git log` 파싱: `\x1e`(RS) 레코드 구분 + `\x00` 필드 구분 → 한글/특수문자 안전 파싱
- `create_bundle`: `git bundle create`가 단순 커밋 해시를 직접 받지 않아 임시 ref(`refs/gitshuttle/tmp_<hash>`) 생성 후 bundle, finally 블록에서 삭제
- `_git_env()` 헬퍼: `PYTHONIOENCODING='utf-8'`, `GIT_TERMINAL_PROMPT='0'` 일괄 적용
- 루트 커밋 `files_changed` 계산 시 `--root` 플래그 분기 처리

### TDD Harness 결과
- SA1: **PASS**
- SA2: **PASS** — 27/27 GREEN
- SA3: **PASS** — 27 passed, 커버리지 79% (핵심 모듈 평균 88%)
- SA4: **PASS** — 인코딩·네트워크·Phase범위·예외처리·파일명패턴 전 항목

### 수락 기준 달성
- [x] `get_commits(repo_path, branch)` → 커밋 목록 반환 (hash, date, author, message, files_changed)
- [x] 한글 커밋 메시지 포함 커밋 정상 파싱
- [x] `create_bundle()` → `.bundle` 파일 생성, `verify_bundle()` → True/False
- [x] `generate(file_path)` → `.sha256` 파일 생성, `verify()` → True/False

---

## Sprint 2 — Export 핵심 + TUI (2026-05-08)

**브랜치:** `sprint/2-export-tui` → `main` merge

### 생성 파일
| 파일 | 내용 |
|------|------|
| `gitshuttle/manifest.py` | `create_manifest()` — UTF-8, BOM 없음 |
| `gitshuttle/export_.py` | `run_export()`, `ExportResult` 데이터클래스 |
| `gitshuttle/ui/__init__.py` | 빈 패키지 |
| `gitshuttle/ui/tui.py` | `select_commits_tui()`, `GITSHUTTLE_HEADLESS=1` headless 분기 |
| `gitshuttle/ui/_textual_app.py` | `CommitSelectorApp` (Textual, Shift 범위선택, 필터, [imported] 표시) |
| `tests/test_manifest.py` | 6개 테스트 |
| `tests/test_export.py` | 6개 테스트 |

### 설계 결정
- TUI headless 테스트: `GITSHUTTLE_HEADLESS=1` 환경변수로 Textual 우회 → 전체 커밋 반환
- `_textual_app.py` 분리: Textual 미설치 환경에서도 `tui.py` import 오류 없도록
- `already_imported` set을 `[imported]` 표시에 활용 (Sprint 4 import_.py 연동 예정)

### TDD Harness 결과
- SA1: **PASS**
- SA2: **PASS** — 39/39 GREEN (신규 12개)
- SA3: **PASS** — 39 passed, 커버리지 69% (manifest 100%, export 97%)
- SA4: **PASS** — WARNING 2건(미사용 import) 즉시 수정 완료

### 수락 기준 달성
- [x] TUI 선택 후 `.bundle` + `.sha256` + `_manifest.txt` 3파일 생성
- [x] manifest에 한글 커밋 메시지 정상 포함
- [x] 기존 커밋 `[imported]` 표시 로직 구현 (already_imported set)
- [x] `gitshuttle export --branch main` 실행 가능

---

## 다음 작업 (Next)

- [ ] Sprint 3: UI 모드 확장 (CSV/HTML/Prompt) + Config
- [ ] GitHub 평가용 repo — Sprint 7 Direct Sync 검증 시에만 최소 사용
