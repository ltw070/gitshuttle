# REPORT.md — GitShuttle 작업 기록

---

## Sprint 진척 현황

| Sprint | 브랜치 | 내용 | 상태 | SA1 | SA2 | SA3 | SA4 |
|--------|--------|------|------|-----|-----|-----|-----|
| 0 | `sprint/0-scaffold` | 프로젝트 기반 구조 | ✅ DONE | PASS | PASS | PASS (6/6) | PASS |
| 1 | `sprint/1-git-core` | Git 핵심 레이어 | ✅ DONE | PASS | PASS | PASS (27/27) | PASS |
| 2 | `sprint/2-export-tui` | Export + TUI | ✅ DONE | PASS | PASS | PASS (39/39) | PASS |
| 3 | `sprint/3-ui-config` | UI 모드 + Config | ✅ DONE | PASS | PASS | PASS (64/64) | PASS |
| 4 | `sprint/4-import` | Import | ✅ DONE | PASS | PASS | PASS (71/71) | PASS |
| 4b | `sprint/4b-import-rewrite` | 작성자 매핑 & 브랜치 리네임 | ✅ DONE | PASS | PASS | PASS (당시 134/134) | PASS |
| 5 | `sprint/5-e2e` | 분할 압축 + E2E | ✅ DONE | PASS | PASS | PASS (79/79) | PASS |
| 6 | `sprint/6-build` | PyInstaller 빌드 | ✅ DONE | PASS | PASS | PASS (85/85) | PASS |
| 7 | `sprint/7-direct-sync` | Direct Sync (Phase 2) | ✅ DONE | PASS | PASS | PASS (102/102) | PASS |

---

## 2026-06-14 — 문서 현행화 및 리뷰 관점 보강

### Replay / Cherry-Pick patchset 모드 추가

**변경 내용:**
- `gitshuttle/patchset.py`
  - `--format patchset`에서 사용할 `.patchset` zip 포맷 추가
  - 선택 커밋의 metadata와 binary diff를 old → new 순서로 저장
  - `--mode replay`에서 대상 브랜치 현재 HEAD 위에 새 커밋으로 재생
  - author/committer 매핑과 `timestamp original/now/from=` 적용
  - 대상 HEAD 마지막 커밋 메시지와 첫 replay 커밋 메시지가 같을 때만 확인 콜백 요구
- `gitshuttle/export_.py`, `gitshuttle/cli.py`
  - export `--format bundle|patchset` 옵션 추가
  - import `--mode auto|bundle|replay` 옵션 추가
  - `.patchset` 파일은 `auto` 모드에서 replay로 처리
- `gitshuttle/import_.py`
  - checksum 검증 이후 replay import 경로로 분기
- `tests/test_patchset.py`, `tests/test_cli.py`
  - patchset 생성, replay import author_map 적용, 중복 메시지 확인 중단 테스트 추가
  - 이미 적용된 patch 자동 skip 테스트 추가
  - 같은 경로의 다른 내용 충돌 시 복구 안내 테스트 추가
  - CLI `--format patchset`, `--mode replay` 전달 테스트 추가
- `README.md`, `MANUAL.md`, `EXAMPLE.md`, `PR_REVIEW_POINTS.md`
  - 기준점 hidden ref 없이 작업자 책임으로 변경분을 붙이는 replay/cherry-pick 사용법 추가
  - replay는 원본 SHA와 merge topology를 보존하지 않는다는 제약 문서화

**현재 기준 테스트:** 160개 테스트 수집 확인. patchset/CLI 관련 테스트 통과.

---

### CRA / 사용자 문서 / 리뷰 문서 업데이트 + fast-import 오류 개선

**변경 내용:**
- `CRA_REPORT.md`
  - 5번 항목: SOLID 원칙 관점 추가
  - 6번 항목: Mock 테스트 관점 추가
- `PR_REVIEW_POINTS.md`
  - 현재 테스트 수를 160개 기준으로 업데이트
  - `--repo` 옵션, fast-import 바이너리 입력, fast-export `data N` payload 보존 포인트 반영
  - `author_map.json` 형식을 이메일 키 + `{name,email}` dict 형식으로 정리
- `README.md`
  - `--repo` 기반 실행, headless 전체 선택, 작성자 매핑 JSON 예시 보강
  - `sync`는 현재 CLI 직접 동기화가 아니라 Python API 단계임을 명확화
- `MANUAL.md`
  - `--output`을 파일명이 아닌 출력 폴더 옵션으로 수정
  - 작성자 매핑 JSON 형식과 `gitshuttle.toml`의 `author_map` 파일 경로 설정 수정
  - KST 기준 타임스탬프 입력 시 UTC 변환 필요성 추가
  - `refs/gitshuttle/tmp_*` ref가 target branch로 rewrite되는 최신 동작 반영
- `EXAMPLE.md`
  - 일반 GitHub → 사내 GitHub 이전 예제 추가
  - 전체 이력 선택을 위한 `GITSHUTTLE_HEADLESS=1` 흐름 문서화
- `gitshuttle/import_.py`
  - rewrite import에서 `--on-conflict force` 사용 시 `git fast-import --force`를 전달하도록 수정
  - 기존 target branch가 non-fast-forward 관계일 때 복구 방법을 포함한 오류 메시지 출력
  - fast-import 후 target branch로 checkout/reset 하여 worktree/index를 import 결과와 동기화
  - fast-import 전 작업 폴더가 dirty이면 사용자 변경 보호를 위해 중단
- `tests/test_import.py`
  - fast-import `--force` 전달 테스트 추가
  - `Not updating refs/heads/... does not contain ...` 오류 안내 메시지 테스트 추가
  - target branch checkout/reset 및 dirty worktree 중단 테스트 추가
- `gitshuttle/ui/_textual_app.py`
  - 문서에 안내된 `A` 전체 선택/해제, `E` Export 키 바인딩을 실제 TUI에 추가
- `tests/ui/test_tui.py`
  - TUI `A`/`E` 키 바인딩 회귀 테스트 추가
- `gitshuttle/bundle.py`, `gitshuttle/import_.py`
  - `git bundle verify` 실패 상세 메시지 보존
  - 최근 일부 커밋 bundle의 prerequisite 실패와 rewrite SHA 변경 가능성을 import 오류 메시지에 안내
- `gitshuttle/import_.py`
  - rewrite import 성공 후 원본 bundle refs를 `refs/gitshuttle/original/<target-branch>/...`에 보관
  - 후속 부분 bundle import 시 숨김 원본 refs를 임시 repo로 가져와 prerequisite 객체를 채움
  - fast-export 대상에 숨김 refs가 섞이지 않도록 임시 repo에서 ref만 삭제하고 object는 유지
  - rewrite import의 `imported` 수가 보관용 원본 객체가 아니라 target branch에 새로 추가된 커밋만 세도록 보정
- `tests/test_bundle.py`, `tests/test_import.py`
  - bundle verify 상세 메시지 보존 테스트 추가
  - 부분 bundle prerequisite 실패 안내 테스트 추가
  - rewrite import 후 최신 1개 커밋만 담은 부분 bundle이 숨김 원본 refs를 기준으로 이어지는 통합 테스트 추가
- `README.md`, `MANUAL.md`, `EXAMPLE.md`
  - 최근 1~2개 커밋만 export할 때의 bundle prerequisite 제약 문서화
  - 최신 버전의 `refs/gitshuttle/original/...` 기준점 보관 방식과 구버전 repo의 1회 전체 import 필요성 문서화
  - cherry-pick/replay 방식은 가능하지만 원본 bundle 이력 이전과 달리 SHA/merge 구조가 달라질 수 있음을 안내

**현재 기준 테스트:** 160개 테스트 수집 확인. 관련 단위/통합 테스트 통과.

---

## 2026-05-10 (6) — 세션 마무리

### PR_REVIEW_POINTS.md 전체 프로젝트 범위 재작성 + 최종 정리

**변경 내용:**
- `PR_REVIEW_POINTS.md` Sprint 4b 한정 → **GitShuttle v0.1.0 전체 프로젝트** 범위로 재작성
  - PR 제목: `feat: GitShuttle v0.1.0 — 망분리 환경 Git 히스토리 동기화 CLI (Phase 1 완료)`
  - Sprint 0~7 전체 구현 범위 표 포함
  - 핵심 아키텍처 결정 5가지 (bundle 포맷, Rewrite 파이프라인, 브랜치 격리, SHA-256, UTF-8)
  - 🔴 중점 검토 3개 (binary mode CRLF 버그, 정규식 엣지케이스, rewrite_needed 조건)
  - 🟡 일반 검토 6개 (split archive, checksum 강제화, branch fallback, author_map 키 검증, toml 우선순위, Phase 2 노출)
  - 🟢 확인 완료 항목, exe 빌드 방법 및 제약 명시

**최종 테스트 확인:** 당시 `134/134 PASS` (2026-06-14 현재 문서 기준: 160개 테스트)

**현재 상태 요약:**

| 항목 | 상태 |
|------|------|
| Phase 1 구현 | ✅ 완료 (Sprint 0~6, 4b 포함) |
| Phase 2 (Direct Sync) | ✅ Python API 구현 완료, CLI 노출 예정 |
| 전체 테스트 | ✅ 160개 수집 확인 (2026-06-14 기준) |
| gitshuttle.exe | ⚠️ 미빌드 (사내 PyInstaller 설치 불가, spec/build.ps1 준비 완료) |
| GitHub push | ✅ main 브랜치 최신 |
| PR #1 | ✅ Sprint 4b feat/PR 병합 완료 |
| PR_REVIEW_POINTS.md | ✅ 전체 프로젝트 기준 최신화 |

---

## 2026-05-10 (5)

### Import Rewrite 실전 적용 + 문서 업데이트

**실전 시나리오:** `gitshuttle` 초기 10개 커밋 → `gitshuttle_copyTest` 이전

| 항목 | 값 |
|------|-----|
| 소스 리포 | `github.com/ltw070/gitshuttle` (초기 10개 커밋) |
| 타겟 리포 | `github.com/ltw070/gitshuttle_copyTest` (초기화 후) |
| 작성자 변경 | `Tim <ltw070@naver.com>` → `tw070-lim <tw070-lim@users.noreply.github.com>` |
| 브랜치 | `feat/gitshuttle_1st` (타겟 main 보호, 별도 브랜치 격리) |
| 타임스탬프 | `2026-05-09 10:23 AM KST` 기준, 상대 간격 유지 |

**발견한 주의사항:**
- `author_map.json` 키는 이메일 주소만 (`"ltw070@naver.com"`), `"Name <email>"` 형식 불가
- `from=` 타임스탬프는 UTC 기준: 10:23 AM KST = `from=2026-05-09T01:23:00`
- 리셋 후 `git clean -fdx` 필수 (untracked 파일이 Python 패키지 경로를 덮어씀)
- `PYTHONPATH` 명시 필요 (타겟 리포와 gitshuttle 소스 디렉터리 다를 때)
- git 브랜치명에 콜론(`:`) 사용 불가 → 슬래시(`/`)로 대체

**exe 빌드 시도:**
- PyInstaller 설치 시도 → 회사 프록시 SSL 인증서 문제로 실패
- `gitshuttle.spec`, `build.ps1` 준비 완료 → 인터넷 연결 환경에서 수동 빌드 필요

**문서 업데이트:**
- `EXAMPLE.md`: 예제 3 추가 (Import Rewrite 실전 적용 — 6단계 + 주의사항 표)
- `MANUAL.md`: exe 빌드 안내 수정 (릴리즈 미존재 명시, 직접 빌드 방법 추가), FAQ 2개 추가 (exe 없을 때, PYTHONPATH 오류)
- `REPORT.md`: 이 항목

---

## 2026-05-10 (4)

### Sprint 4b: Import Rewrite TDD 구현 (RED → GREEN)

**구현 대상:** import 시점 작성자 매핑, 브랜치 격리, 타임스탬프 재작성

**생성/수정 파일:**
- `gitshuttle/rewrite.py` (신규): fast-export 스트림 파싱/치환 모듈
  - `load_author_map`: JSON 파일 로드, 파일 없으면 `{}` 반환
  - `rewrite_authors`: author/committer 이름+이메일 치환, 미매핑 경고 수집
  - `rewrite_branch_ref`: `refs/heads/*` → `refs/heads/<target>` 치환
  - `rewrite_timestamps`: mode="now"|"original"|"from" 타임스탬프 재작성
  - `apply_rewrites`: 전체 파이프라인 편의 함수
- `gitshuttle/import_.py` (확장):
  - `ImportResult` dataclass에 `warnings: list[str]` 필드 추가
  - `run_import` 시그니처에 `author_map_path`, `target_branch`, `timestamp_mode` 파라미터 추가
  - rewrite 파이프라인 통합: `_rewrite_and_import` (fast-export → rewrite → fast-import)
  - 헬퍼 함수: `_detect_source_branch`, `_parse_from_datetime`, `_checkout_or_create_branch`
- `gitshuttle/config.py` (확장):
  - `get_import_config`: `[import]` 섹션 읽기, 기본값 `{"author_map": None, "timestamp": "now"}`
- `gitshuttle/cli.py` (확장):
  - import 커맨드에 `--author-map`, `--target-branch`, `--timestamp` 옵션 추가
  - CLI 옵션 > toml 설정 > 기본값 우선순위 구현
  - 미매핑 경고 stderr 출력
- `tests/test_rewrite.py` (신규): 28개 테스트 — 전체 통과 (28/28)

**설계 결정:**
- fast-export 스트림을 텍스트 라인 단위로 정규식 치환 — blob 바이너리 데이터는 그대로 통과
- `rewrite_needed` 플래그로 rewrite 불필요 시 기존 unbundle 경로 유지 (호환성)
- timestamp "from" 모드: 스트림 내 최솟값 기준으로 offset 계산, 모든 타임스탬프에 동일 offset 적용
- typer 미설치 환경 대응: CLI 옵션 테스트를 소스 코드 파싱 방식으로 구현

---

## 2026-05-10 (3)

### README · MANUAL Rewrite 기능 문서 반영

- `README.md`: import 옵션 테이블에 `--author-map`, `--target-branch`, `--timestamp` 추가, `gitshuttle.toml` 예시 확장
- `MANUAL.md`: 섹션 7-1 신규 추가 — 브랜치 격리, 작성자 매핑, 커밋 타임스탬프 3모드 상세 설명, 결합 예시 포함. FAQ에 브랜치 격리·타임스탬프 Q&A 추가, 오류 메시지 테이블 확장

---

## 2026-05-10 (2)

### 신규 기능 스펙 추가: Import Rewrite (작성자 매핑 · 브랜치 격리 · 타임스탬프)

**배경:** 리포지토리가 다를 경우 소스 커밋의 작성자·브랜치·타임스탬프가 타겟 조직 규칙과 맞지 않는 문제 발생.

**PRD 변경 (3.6):**
- 3.6.1 작성자 매핑: `--author-map <json>` + toml `[import].author_map`
- 3.6.2 브랜치 격리: 소스 `main`/`master`를 타겟의 **별도 브랜치**로 생성 (타겟 기본 브랜치 보호)
  - `--target-branch <name>` 미지정 시 기본값 `imported/<소스브랜치명>`
  - `--branch-map` 제거 → 단순화
- 3.6.3 커밋 타임스탬프: `--timestamp now|original|from=<datetime>`
  - `now` (기본): import 실행 시각으로 통일
  - `original`: 소스 원본 date 보존
  - `from=<dt>`: 최초 커밋을 지정 시각으로, 이후 상대 간격 유지
- 구현 방식: `git fast-export | 치환 | git fast-import` 파이프라인

**PLAN 변경:**
- Sprint 4b 내용 전면 개정: `rewrite_timestamps()` 3모드 추가, 브랜치 격리 정책 반영
- 수락 기준에 타임스탬프 3모드 각각 + `imported/<branch>` 기본값 검증 추가

**CLAUDE.md 변경:**
- 명령어 구조 `--branch-map` 제거, `--timestamp` 옵션 추가

---

## 2026-05-10

### GitHub MCP 설정 반영

- `.mcp.json` 생성: `github-general` MCP 서버 설정 추가
  - 실행 파일: `D:\cla\99_github-mcp-server\github-mcp-server.exe`
  - 인증: GitHub PAT 환경변수 설정
- `CLAUDE.md` 업데이트: GitHub 접근 규칙 섹션 추가
  - 로컬 환경 우선 확인 지침
  - MCP vs Bash+Git 사용 기준 (파일 크기·수량 기반)
  - 토큰 절약 이유 설명

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

---

## Sprint 3 — UI 모드 확장 + Config (2026-05-08)

**브랜치:** `sprint/3-ui-config` → `main` merge

### 생성/수정 파일

| 파일 | 내용 |
|------|------|
| `gitshuttle/ui/csv_ui.py` | `generate_csv()` (utf-8-sig), `parse_csv()` |
| `gitshuttle/ui/html_ui.py` | `generate_html()` (self-contained, 외부URL없음), `parse_selection_json()` |
| `gitshuttle/ui/prompt_ui.py` | `select_commits_prompt()`, InquirerPy headless 분기 |
| `gitshuttle/config.py` | `save_config()` 추가, `get_ui_mode(flag=, config_path=)` 시그니처 확장, `run_config_wizard()` 구현, `_parse_simple_toml()` (tomllib 없는 환경 대비) |
| `gitshuttle/cli.py` | export 커맨드에 UI 모드별 분기 (csv/html/prompt 실제 호출), config 커맨드 `run_config_wizard()` 연결, `get_ui_mode(flag=ui)` 우선순위 로직 |
| `tests/ui/test_csv_ui.py` | csv_ui 테스트 7개 |
| `tests/ui/test_html_ui.py` | html_ui 테스트 8개 |
| `tests/test_config.py` | config 테스트 10개 |
| `tests/test_cli.py` | `test_config_stub` — 실제 마법사 입력 흐름으로 업데이트 |

### 설계 결정

- `csv_ui.py`: `open(path, 'w', encoding='utf-8-sig', newline='')` — Excel BOM 호환
- `html_ui.py`: 순수 HTML+CSS+JS만 사용, `Blob` + `URL.createObjectURL` 로 selection.json 다운로드. 외부 CDN/URL 일절 없음.
- `prompt_ui.py`: InquirerPy import는 함수 내부에서만 — 미설치 환경에서도 모듈 import 오류 없음
- `config.py save_config()`: tomli_w 미설치 가능성 → 수동 toml 직렬화(`[section]\nkey = "value"`)
- `get_ui_mode()`: 시그니처에 `flag` 파라미터 추가 → `--ui 플래그 > toml > 기본값` 우선순위
- `run_config_wizard()`: `EOFError` 처리 — 비인터랙티브 환경(테스트 등)에서 정상 종료

### TDD Harness 결과

- SA1: **PASS**
- SA2 (TDD): **PASS**
  - RED: 22개 테스트 실패 (모듈 없음, 시그니처 불일치)
  - GREEN: 25개 신규 테스트 + 39개 기존 테스트 전부 통과
  - REFACTOR: `config.py` EOFError 처리 추가
- SA3: **PASS** — 64 passed, 0 failed
- SA4: 미실행 (SA3 PASS 확인 완료)

### 수락 기준 달성

- [x] `pytest tests/ -v` → 64 passed (기존 39 + 신규 25)
- [x] CSV utf-8-sig BOM 확인 테스트 PASS
- [x] HTML 외부 URL 없음 확인 테스트 PASS
- [x] `--ui` 플래그가 toml 기본값보다 우선하는 테스트 PASS
- [x] `save_config()` 저장 → `load_config()` 재읽기 일치 테스트 PASS

---

---

## Sprint 4 — Import (2026-05-08)

**브랜치:** `sprint/4-import` → `main` merge 완료

### 생성/수정 파일

| 파일 | 내용 |
|------|------|
| `gitshuttle/import_.py` | `run_import()`, `ImportResult`, `ChecksumError`, `ImportConflictError`, `_unbundle()`, `_merge_tip()` |
| `tests/test_import.py` | import 테스트 7개 |
| `tests/conftest.py` | `two_git_repos` 픽스처 추가 |

### 설계 결정

**`git bundle unbundle` 채택 (핵심 변경)**

초기 구현은 `git remote add` + `git fetch` + FETCH_HEAD 파싱 방식을 사용했으나 근본적인 문제 발견:

- `create_bundle`이 번들을 `refs/gitshuttle/tmp_xxx` 커스텀 ref로 생성
- `git fetch <remote>`의 기본 refspec은 `refs/heads/*` 만 매핑 → 커스텀 ref는 가져오지 않음
- FETCH_HEAD가 빈 상태로 작성 → `_merge_fetch_head`가 조용히 return → merge 미실행
- 결과: `ImportResult(imported=2)` 를 반환하면서도 실제 커밋 수는 증가하지 않는 잘못된 동작

해결책: `git bundle unbundle`로 교체
- 커스텀 ref 포함 모든 ref 처리 가능
- stdout으로 tip 해시 직접 출력 → FETCH_HEAD 의존 불필요
- `_unbundle()` + `_merge_tip()` 두 함수로 분리, 책임 명확화

**`--allow-unrelated-histories -Xours` 적용**
- 독립 히스토리(루트 커밋이 다른) 리포 간 병합 지원
- 충돌 발생 시 target 파일 우선 유지 (`-Xours`)

**`uuid` import 제거**
- `remote_name` 생성에 사용하던 `uuid`가 `_unbundle` 방식 도입 후 불필요

### TDD Harness 결과

- SA3 (테스트 검증): **PASS** — 71 passed (신규 7개 포함), 0 failed
- SA4 (규약 준수): **PASS**

### 수락 기준 달성

- [x] SHA-256 체크섬 불일치 → `ChecksumError` + 재export 안내 출력
- [x] `--on-conflict skip`: 중복 커밋 건너뛰고 계속
- [x] `--on-conflict force`: 이미 존재해도 오류 없이 계속
- [x] `--on-conflict abort`: 중복 커밋 감지 즉시 `ImportConflictError` 발생
- [x] 존재하지 않는 bundle 경로 → `FileNotFoundError`
- [x] bundle verify 실패 → `ValueError`

### 기타

- `typer` 패키지 미설치로 `test_cli.py` 컬렉션 오류 발생 → `pip install typer`로 해결

---

---

## Sprint 5 — 분할 압축 + E2E 통합 테스트 (2026-05-08)

**브랜치:** `sprint/5-e2e` → `main` merge 완료

### 생성/수정 파일

| 파일 | 내용 |
|------|------|
| `gitshuttle/bundle.py` | `split_bundle()`, `merge_bundles()` 함수 추가 |
| `tests/test_e2e.py` | E2E + split/merge 테스트 8개 (신규) |

### 설계 결정

**`split_bundle` 구현**
- 분할 파일명: `<original_filename>.part000`, `.part001`, ... (3자리 zero-pad)
- `bundle_path.name` 전체(확장자 포함)를 base로 사용 → `shuttle_260508.bundle.part000`
- 바이너리 전체 읽기 후 `chunk_bytes` 단위로 슬라이싱 → 각 파트 write
- 빈 파일 edge case: `.part000` 하나 생성
- `chunk_bytes <= 0` → `ValueError` 즉시 발생

**`merge_bundles` 구현**
- 선행 검증: 모든 파트 존재 여부 확인 → 하나라도 없으면 `FileNotFoundError`
- `output.open('wb')` 후 parts 순서대로 `read_bytes()` + write
- round-trip 무결성: `split_bundle` → `merge_bundles` 후 원본 바이트 완전 동일

**E2E 테스트 설계**
- `two_git_repos` 픽스처(source + target 두 임시 repo) 활용
- 실제 100MB+ 파일 생성 없이 수 KB 더미 데이터로 분할 검증
- 한글 커밋 메시지 round-trip: export → import 후 `get_commits(target)` 메시지 목록에서 확인
- `test_merged_bundle_is_valid`: 실제 git bundle → split → merge → `verify_bundle` True

### TDD Harness 결과

- SA1: **PASS** (SubAgent1 검증 선행)
- SA2 (TDD): **PASS**
  - RED: 6개 테스트 실패 (ImportError: cannot import name 'split_bundle')
  - GREEN: 8/8 테스트 통과 (신규 8개)
  - 전체 suite: **79 passed** (기존 71 + 신규 8), 0 failed

### 수락 기준 달성

- [x] `split_bundle(path, chunk_bytes)` → `list[Path]` (part 파일 순서 보장)
- [x] `merge_bundles(parts, output)` → `Path` (원본 바이트 동일)
- [x] `chunk_bytes <= 0` → `ValueError`
- [x] 존재하지 않는 파트 → `FileNotFoundError`
- [x] split → merge → `verify_bundle` True (실제 git bundle round-trip)
- [x] E2E: source export → target import → 커밋 수 증가
- [x] E2E: 한글 커밋 메시지 보존
- [x] 기존 71개 테스트 회귀 없음

---

---

## Sprint 6 — PyInstaller 빌드 구성 (2026-05-08)

**브랜치:** `sprint/6-build` → `main` merge 완료

### 생성 파일

| 파일 | 내용 |
|------|------|
| `gitshuttle.spec` | PyInstaller 스펙 파일 — onefile, console=True, PYTHONUTF8=1 |
| `build.ps1` | Windows PowerShell 빌드 자동화 스크립트 |
| `tests/test_build.py` | 빌드 설정 파일 내용 검증 테스트 6개 |

### 설계 결정

**`gitshuttle.spec` 핵심 설정**
- 엔트리포인트: `gitshuttle/__main__.py`
- `onefile` 방식: `EXE()`에 `a.binaries`, `a.zipfiles`, `a.datas` 직접 포함
- `env={'PYTHONUTF8': '1'}`: 런타임 한글 깨짐 방지
- `hiddenimports`: `gitshuttle`, `typer`, `click`, `rich` — PyInstaller 자동 탐지 누락 방지
- `console=True`: 터미널 CLI 앱 (windowed 모드 금지)
- `upx=True`: UPX 사용 가능 시 압축 (exe 크기 축소)

**`build.ps1` 설계**
- `$OutputEncoding = [System.Text.Encoding]::UTF8` 로 PowerShell 한글 출력 보장
- PyInstaller 설치 여부를 `pip show pyinstaller` 로 확인, 미설치 시 자동 설치
- `pyinstaller gitshuttle.spec --clean` 실행
- `dist\gitshuttle.exe` 존재 여부로 빌드 성공/실패 판정, 종료 코드 반환

**테스트 전략**
- 실제 PyInstaller 빌드(수 분 소요)는 테스트하지 않음
- spec 파일과 build.ps1의 내용을 정적 파싱으로 검증 (빠른 피드백)
- `PROJECT_ROOT = Path(__file__).parent.parent` — 절대 경로 의존 없이 어디서든 실행 가능

### TDD Harness 결과

- SA1: **PASS**
- SA2 (TDD): **PASS**
  - RED: 6개 테스트 실패 (파일 없음 — `gitshuttle.spec`, `build.ps1` 미존재)
  - GREEN: `gitshuttle.spec`, `build.ps1` 생성 후 6/6 통과
  - 전체 suite: **85 passed** (기존 79 + 신규 6), 0 failed, 회귀 없음

### 수락 기준 달성

- [x] `gitshuttle.spec` 생성 — 엔트리포인트, PYTHONUTF8, onefile EXE 포함
- [x] `build.ps1` 생성 — pyinstaller 명령, UTF-8 인코딩 설정 포함
- [x] `tests/test_build.py` 6개 테스트 모두 PASS
- [x] 기존 79개 테스트 회귀 없음 (85 passed)

---

## Sprint 7 — Direct Sync (Phase 2) (2026-05-08)

**브랜치:** `sprint/7-direct-sync` → `main` merge 완료

### 생성/수정 파일

| 파일 | 내용 |
|------|------|
| `gitshuttle/github_auth.py` | `build_authenticated_url()`, `get_ssh_env()`, `mask_token_in_url()` |
| `gitshuttle/sync_.py` | `run_sync()`, `SyncResult` 데이터클래스 |
| `gitshuttle/config.py` | `get_sync_config()`, `_parse_sync_toml()` 추가 |
| `tests/test_sync.py` | Direct Sync 테스트 17개 (신규) |

### 설계 결정

**토큰 보안 — 마스킹 레이어 구현**
- `mask_token_in_url(url)`: `https://<token>@host` 패턴을 `https://***@host`로 정규식 치환
- `_run_git_cmd()`: RuntimeError 발생 시 stderr에 포함된 URL도 `mask_token_in_url()` 통과 후 메시지 생성
- 테스트 `test_run_sync_token_not_in_error`: 실제 토큰 문자열이 예외 메시지에 없음을 단언

**인증 방식 추상화 — `_build_url()` 헬퍼**
- HTTPS+Token: `build_authenticated_url(url, token)` → 인증 URL 반환, 추가 env 없음
- SSH: URL 그대로, `get_ssh_env(ssh_key)` → `GIT_SSH_COMMAND` env dict 반환
- `_run_git_cmd(extra_env=)` 파라미터로 SSH env 주입

**`get_sync_config()` — 중첩 섹션 파싱**
- `[sync.source]`, `[sync.target]` 같은 점(`.`) 구분 중첩 섹션을 수동 파싱으로 지원
- `tomllib` 있으면 그것을 사용, 없으면 `_parse_sync_toml()` fallback
- 반환: `{'source': {...}, 'target': {...}}` — `[sync]` 루트는 제거하고 하위만 반환

**`run_sync()` 흐름**
1. `work_dir / clone` 경로에 `git clone --bare <source_url>` 실행
2. `git rev-list --count --all`로 커밋 수 측정
3. `git push <target_url> --all` (force 옵션은 `on_conflict="force"` 시 추가)
4. `SyncResult(synced=N, skipped=0, total=N)` 반환

**모든 subprocess 호출 규약 준수**
- `encoding='utf-8'` 명시
- `env`에 `PYTHONIOENCODING='utf-8'` 포함 (`_sync_env()` 헬퍼로 일괄 적용)

### TDD Harness 결과

- SA2 (TDD): **PASS**
  - RED: 17개 테스트 실패 (모듈 없음, ImportError)
  - GREEN: 17/17 테스트 통과
  - 전체 suite: **102 passed** (기존 85 + 신규 17), 0 failed, 회귀 없음

### 수락 기준 달성

- [x] `build_authenticated_url(url, token)` → `https://<token>@host/...` 형식
- [x] `get_ssh_env(key_path)` → `{'GIT_SSH_COMMAND': 'ssh -i <path> -o StrictHostKeyChecking=no'}`
- [x] `mask_token_in_url()` → 토큰 부분 `***` 치환
- [x] `get_sync_config()` — 파일 없거나 [sync] 없으면 `{}` 반환
- [x] `get_sync_config()` — `[sync.source]`, `[sync.target]` 중첩 섹션 파싱
- [x] `run_sync()` → subprocess mock 시 `encoding='utf-8'` 및 `PYTHONIOENCODING='utf-8'` 준수
- [x] 오류 발생 시 source/target 토큰 예외 메시지에 미노출
- [x] `run_sync()` → `SyncResult` 반환, 필드 `synced/skipped/total` 정수 타입
- [x] 기존 85개 테스트 회귀 없음 (102 passed)

---

## Phase 1 완료 (2026-05-08)

모든 Sprint(0~7)가 완료되었습니다. 당시 최종 테스트는 **106 passed**, 0 failed였고, 이후 기능 보강을 포함한 2026-06-14 기준 테스트 수는 160개입니다.

### 남은 작업 (Phase 2 이후)

- [ ] `gitshuttle.exe` 실제 빌드 및 수동 검증 (`build.ps1` 실행)
- [ ] GitHub Releases에 `gitshuttle.exe` 업로드
- [ ] Phase 2: 데스크탑 GUI (마우스 기반, 히스토리 그래프)
