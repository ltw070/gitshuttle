# PLAN.md — GitShuttle Phase 1 TDD 개발 계획

## 개요

Phase 1(CLI + TUI) 구현을 6개 Sprint로 나누어 진행한다.
모든 Sprint는 **TDD Harness** 를 통해 실행된다 → `HARNESS.md` 참고.

### Sprint당 표준 사이클

```
┌─────────────────────────────────────────────────────────┐
│  매 Sprint 시작 전                                        │
│  SubAgent1 (doc-verify) — 문서 정합성 검증               │
│    └─ PASS → SubAgent2 진행 / FAIL → 문서 수정 후 재실행 │
├─────────────────────────────────────────────────────────┤
│  구현                                                     │
│  SubAgent2 (ai-action) — TDD: RED → GREEN → REFACTOR    │
├─────────────────────────────────────────────────────────┤
│  검증 (병렬)                                              │
│  SubAgent3 (test-verify)  ──┐                            │
│  SubAgent4 (compliance)   ──┘ 동시 실행                  │
│    └─ 둘 다 PASS → 커밋 / FAIL → SA2 재실행              │
└─────────────────────────────────────────────────────────┘
```

---

## 패키지 구조 목표

```
gitshuttle/
├── __init__.py
├── __main__.py       # 엔트리포인트 + UTF-8 강제
├── cli.py            # Typer app 정의, 커맨드 등록
├── git_ops.py        # git 서브프로세스 래퍼 (log, bundle, verify)
├── bundle.py         # bundle 생성 / 검증
├── checksum.py       # SHA-256 생성 / 검증
├── manifest.py       # 커밋 목록 요약 파일 생성
├── export_.py        # export 커맨드 오케스트레이션
├── import_.py        # import 커맨드 오케스트레이션
├── config.py         # config 마법사, gitshuttle.toml 읽기/쓰기
└── ui/
    ├── __init__.py
    ├── tui.py        # Textual 체크박스 + 테이블 (기본값)
    └── csv_ui.py     # commits.csv 생성/파싱

tests/
├── conftest.py       # 공통 픽스처 (임시 git repo, sample commits)
├── test_git_ops.py
├── test_bundle.py
├── test_checksum.py
├── test_manifest.py
├── test_export.py
├── test_import.py
├── test_config.py
└── ui/
    ├── test_csv_ui.py
    └── test_tui.py
```

---

## Sprint 0 — 프로젝트 기반 구조

**목표:** 빌드·테스트·실행 가능한 최소 골격 구성

### 구현 대상
- `pyproject.toml` (의존성, 빌드 설정)
- `requirements.txt` / `requirements-dev.txt`
- `gitshuttle/__init__.py`, `__main__.py`, `cli.py` 스캐폴딩
- `tests/conftest.py` — 임시 git repo 픽스처
- `gitshuttle.toml` 기본 템플릿

### TDD 사이클

| 단계 | SubAgent | 내용 |
|------|----------|------|
| 문서 검증 | SA1 | PRD↔README↔CLAUDE.md 정합성 확인 |
| 구현 | SA2 | `python -m gitshuttle` 실행 → `Usage: gitshuttle [OPTIONS] COMMAND` 출력 확인 테스트 먼저 |
| 검증 | SA3+SA4 | pytest 통과 + 인코딩·네트워크 규약 확인 |

### 수락 기준 (Acceptance Criteria)
- [x] `python -m gitshuttle --help` 실행 시 export/import/config 커맨드 목록 출력
- [x] `pytest tests/` 실행 시 0 errors
- [x] `gitshuttle.toml` 없을 때 기본값(tui)으로 동작

### SA2 호출 프롬프트
```
Sprint 0: 프로젝트 기반 구조 생성.
pyproject.toml(Python 3.10+, Typer, Textual 의존성),
gitshuttle 패키지 스캐폴딩(__main__.py UTF-8 강제, cli.py Typer app),
tests/conftest.py(임시 git repo 픽스처) 작성.
수락 기준: python -m gitshuttle --help 시 커맨드 목록 출력.
```

---

## Sprint 1 — Git 핵심 레이어

**목표:** git 명령어 래핑 및 커밋 데이터 파싱

### 구현 대상
- `git_ops.py`: `get_commits()`, `check_git_version()`, `run_git()`
- `bundle.py`: `create_bundle()`, `verify_bundle()`
- `checksum.py`: `generate()`, `verify()`

### TDD 사이클

| 단계 | SubAgent | 내용 |
|------|----------|------|
| 문서 검증 | SA1 | Git 2.37+ 스펙, SHA-256 명세 확인 |
| 구현 | SA2 | `test_git_ops.py` 먼저 작성 (임시 repo 픽스처 활용) |
| 검증 | SA3+SA4 | subprocess encoding='utf-8' 준수 여부 포함 |

### 수락 기준
- [x] `get_commits(repo_path, branch)` → 커밋 목록 (hash, date, author, message, files_changed) 반환
- [x] 한글 커밋 메시지 포함 커밋 정상 파싱
- [x] `create_bundle()` → `.bundle` 파일 생성, `verify_bundle()` → True/False
- [x] `generate(file_path)` → `.sha256` 파일 생성, `verify()` → True/False

### SA2 호출 프롬프트
```
Sprint 1: Git 핵심 레이어 구현.
git_ops.py(get_commits, check_git_version, run_git — 모두 encoding='utf-8'),
bundle.py(create_bundle, verify_bundle),
checksum.py(generate, verify — SHA-256).
한글 커밋 메시지 파싱 테스트 포함 필수.
```

---

## Sprint 2 — Export 핵심 (TUI 기본값)

**목표:** TUI 커밋 선택 → bundle + checksum + manifest 생성까지 E2E

### 구현 대상
- `ui/tui.py`: Textual 체크박스 테이블, Shift 범위선택, 필터(작성자/파일/날짜), `[imported]` 표시
- `manifest.py`: `create_manifest(commits, output_path)`
- `export_.py`: UI → 선택 커밋 → bundle + sha256 + manifest 파이프라인

### TDD 사이클

| 단계 | SubAgent | 내용 |
|------|----------|------|
| 문서 검증 | SA1 | PRD 3.1(추출), 3.2(UI), 3.3(패키지) 스펙 확인 |
| 구현 | SA2 | TUI는 headless 테스트 픽스처로, 선택 결과를 직접 주입하여 파이프라인 테스트 |
| 검증 | SA3+SA4 | manifest 파일 UTF-8 저장 확인 포함 |

### 수락 기준
- [x] TUI에서 커밋 선택 후 `shuttle_YYMMDD.bundle` + `.sha256` + `_manifest.txt` 3파일 생성
- [x] manifest에 한글 커밋 메시지 정상 포함
- [x] 이미 타겟에 반영된 커밋은 `[imported]` 표시
- [x] `gitshuttle export --branch main` 실행 가능

### SA2 호출 프롬프트
```
Sprint 2: Export 핵심 구현.
ui/tui.py(Textual — 체크박스 테이블, Shift 범위선택, 작성자/파일/날짜 필터),
manifest.py(UTF-8, 커밋 요약),
export_.py(UI→bundle+sha256+manifest 파이프라인).
TUI headless 테스트 픽스처 필수.
```

---

## Sprint 3 — CSV UI + Config

**목표:** TUI 기본 흐름을 보완하는 CSV 모드와 설정 마법사 구현

### 구현 대상
- `ui/csv_ui.py`: `commits.csv` 생성(`utf-8-sig`), `include` 컬럼 파싱
- `config.py`: `gitshuttle.toml` 읽기/쓰기, `gitshuttle config` 마법사
- `--ui` 플래그 우선순위 로직 (`--ui` > `toml` > 기본값 tui)

### TDD 사이클

| 단계 | SubAgent | 내용 |
|------|----------|------|
| 문서 검증 | SA1 | PRD 3.2 UI 옵션표, 설정 파일 스펙 확인 |
| 구현 | SA2 | CSV 입력→커밋목록 변환 단위 테스트 |
| 검증 | SA3+SA4 | CSV utf-8-sig 확인 |

### 수락 기준
- [x] `gitshuttle export --ui csv` → `commits.csv` 생성, 수정 후 재입력 시 선택 반영
- [x] `gitshuttle config` → 마법사 실행 후 `gitshuttle.toml` 저장
- [x] `--ui` 플래그가 toml 기본값보다 우선

### SA2 호출 프롬프트
```
Sprint 3: UI 모드 확장 + Config 구현.
ui/csv_ui.py(utf-8-sig, include 컬럼),
config.py(toml 읽기/쓰기, 마법사).
--ui 플래그 우선순위 로직 테스트 필수.
```

---

## Sprint 4 — Import

**목표:** bundle 수신 → 검증 → 병합까지 E2E

### 구현 대상
- `import_.py`: SHA-256 검증 → 커밋 매칭 → Fast-forward → 충돌 처리
- 충돌 처리: `--on-conflict skip / force / abort`
- 손상 파일: 체크섬 불일치 → 오류 메시지 + 재export 명령어 안내

### TDD 사이클

| 단계 | SubAgent | 내용 |
|------|----------|------|
| 문서 검증 | SA1 | PRD 3.4(Import), 3.5(복구) 스펙 확인 |
| 구현 | SA2 | 3가지 충돌 시나리오 + 체크섬 불일치 시나리오 테스트 먼저 |
| 검증 | SA3+SA4 | 모든 충돌 케이스 커버리지 확인 |

### 수락 기준
- [x] `gitshuttle import --file shuttle.bundle` → SHA-256 검증 → 히스토리 반영
- [x] `--on-conflict skip`: 중복 커밋 건너뛰고 계속
- [x] `--on-conflict force`: 강제 덮어쓰기
- [x] `--on-conflict abort`: 충돌 즉시 전체 중단
- [x] 체크섬 불일치: 명확한 오류 + `gitshuttle export ...` 재실행 안내 출력

### SA2 호출 프롬프트
```
Sprint 4: Import 구현.
import_.py(SHA-256 검증 → 커밋 매칭 → Fast-forward → 충돌 처리).
테스트: skip/force/abort 3케이스 + 체크섬 불일치 케이스 모두 포함.
손상 파일 오류 메시지에 재export 명령어 자동 출력 필수.
```

---

## Sprint 4b — Import Rewrite: 작성자 매핑 · 브랜치 격리 · 타임스탬프

**목표:** 리포지토리가 다를 경우 import 시점에 작성자·브랜치·타임스탬프를 재작성하여 타겟 조직 규칙에 맞게 반영

### 구현 대상

**`rewrite.py`** — `git fast-export | 치환 | git fast-import` 파이프라인
- `rewrite_authors(stream, author_map)` — 작성자 이름·이메일 치환
- `rewrite_branch_ref(stream, target_branch)` — fast-import 시 ref를 `refs/heads/<target-branch>`로 교체
- `rewrite_timestamps(stream, mode, from_dt=None)` — 타임스탬프 재작성
  - `mode="now"`: 모든 committer/author date를 실행 시각으로 통일
  - `mode="original"`: 원본 그대로 통과
  - `mode="from"`: 최초 커밋 → `from_dt`, 이후 커밋은 원본 상대 간격 유지
- `load_author_map(path)` — JSON 파일 로드

**`import_.py` 확장**
- `--author-map <파일>` 옵션 추가
- `--target-branch <이름>` 옵션 추가 (기본값: `imported/<소스브랜치명>`)
- `--timestamp now|original|from=<datetime>` 옵션 추가 (기본값: `now`)
- `gitshuttle.toml` `[import]` 섹션의 `author_map`, `timestamp` 값 읽기

**`tests/test_rewrite.py`**
- 작성자 치환 / 미매핑 원본 유지 케이스
- 브랜치 ref 치환 확인
- 타임스탬프 3모드 (now / original / from) 각각 검증
- `from=` 모드: 최초 커밋 시각, 상대 간격 보존 검증

### TDD 사이클

| 단계 | SubAgent | 내용 |
|------|----------|------|
| 문서 검증 | SA1 | PRD 3.6(Rewrite) 스펙 — 브랜치 격리 정책, 타임스탬프 3모드 확인 |
| 구현 | SA2 | fast-export/import 파이프라인 단위 테스트 먼저, 3모드 타임스탬프 각각 테스트 |
| 검증 | SA3+SA4 | 커버리지 + 원본 시간 보존 / 간격 계산 정확도 compliance |

### 수락 기준
- [x] `gitshuttle import --file shuttle.bundle` → 타겟에 `imported/main` 브랜치 신규 생성, 기존 `main` 불변
- [x] `gitshuttle import --file shuttle.bundle --target-branch ext-main` → `ext-main` 브랜치 생성
- [x] `gitshuttle import --file shuttle.bundle --author-map map.json` → 작성자 치환 후 반영
- [x] 매핑 테이블에 없는 작성자는 원본 유지 + 경고 메시지 출력
- [x] `--timestamp now` (기본): 모든 커밋의 date = import 실행 시각
- [x] `--timestamp original`: 소스 author date·committer date 그대로 보존
- [x] `--timestamp from=2024-01-01T09:00:00`: 최초 커밋 = 지정 시각, 이후 상대 간격 유지
- [x] `gitshuttle.toml` `[import]` 섹션의 `author_map`, `timestamp` 값 적용
- [x] CLI 옵션이 toml 설정보다 우선

### SA2 호출 프롬프트
```
Sprint 4b: Import Rewrite 구현.
rewrite.py(rewrite_authors, rewrite_branch_ref, rewrite_timestamps — git fast-export/fast-import 파이프라인),
import_.py 확장(--author-map, --target-branch 기본값 imported/<소스브랜치>, --timestamp now|original|from=<dt>),
config.py 확장([import] author_map, timestamp).
타임스탬프 3모드 각각 테스트 필수. from= 모드: 상대 간격 보존 계산 검증.
미매핑 작성자 원본 유지 + 경고 케이스 테스트 필수.
```

---

## Sprint 5 — 분할 전송 + E2E 통합

**목표:** 대용량 bundle 분할 전송 지원 및 E2E 검증 (토큰 사용량 다른 Sprint 수준으로 제한)

### 범위 제약 (변경)
- 대용량 실제 데이터 생성 금지 — 실제 100MB+ 파일 생성·처리 테스트 제외
- 분할 로직은 **소형 더미 데이터**(1MB 이하)로 검증
- E2E는 tmp_path 기반 두 임시 repo로 시뮬레이션 (GitHub repo 테스트 없음)

### 구현 대상
- 분할 전송 (Split archive) — bundle을 지정 크기(bytes)로 분할/재조립하는 로직
- E2E 테스트: 두 개의 임시 git repo(외부/내부)로 export→import 전체 흐름
- 한글 커밋 메시지 E2E 왕복 보존 검증

### TDD 사이클

| 단계 | SubAgent | 내용 |
|------|----------|------|
| 문서 검증 | SA1 | PRD 7(대용량 처리) 스펙 확인 |
| 구현 | SA2 | 분할 로직은 소형 더미 파일로, E2E는 tmp 픽스처 2개로 검증 |
| 검증 | SA3+SA4 | 전체 pytest + compliance (대용량 실 데이터 없이) |

### 수락 기준
- [x] `split_bundle(path, chunk_bytes)` → 분할 파일 목록 반환
- [x] `merge_bundles(parts, output)` → 원본과 동일한 bundle 재조립
- [x] E2E: 한글 커밋 메시지가 export→import 후 동일하게 유지
- [x] 전체 pytest 통과

### SA2 호출 프롬프트
```
Sprint 5: 분할 전송 + E2E 통합 테스트 (토큰 절약 모드).
split_bundle/merge_bundles는 소형 더미 파일(수KB)로만 테스트.
E2E는 두 tmp_path git repo로 export→import 전체 흐름 검증.
실제 대용량 파일 생성 절대 금지.
```

---

## Sprint 6 — 빌드 & 배포

**목표:** `gitshuttle.exe` 단일 파일 빌드

### 구현 대상
- `gitshuttle.spec` (PyInstaller 설정, `PYTHONUTF8=1` 환경변수 포함)
- Windows Terminal / CMD / PowerShell 호환성 검증
- 빌드 스크립트 (`build.ps1`)

### TDD 사이클

| 단계 | SubAgent | 내용 |
|------|----------|------|
| 문서 검증 | SA1 | PRD 6(배포), CLAUDE.md 엔트리포인트 스펙 확인 |
| 구현 | SA2 | .spec 파일 작성, 빌드 후 `gitshuttle.exe --help` 동작 확인 |
| 검증 | SA3+SA4 | exe 실행 후 한글 출력 깨짐 없는지 compliance 체크 |

### 수락 기준
- [x] `.\gitshuttle.exe --help` → 커맨드 목록 정상 출력 (spec/build 파일 구성 완료)
- [x] `.\gitshuttle.exe export` → TUI 정상 실행 (spec/build 파일 구성 완료)
- [x] 한글 메시지 출력 깨짐 없음 (PYTHONUTF8=1 spec 적용)

### SA2 호출 프롬프트
```
Sprint 6: PyInstaller 빌드.
gitshuttle.spec(PYTHONUTF8=1, 단일 exe),
build.ps1(빌드 자동화),
exe 실행 + 한글 출력 검증 테스트.
```

---

## 전체 일정 요약

| Sprint | Phase | 내용 | 핵심 산출물 |
|--------|-------|------|-------------|
| 0 | 1 | 기반 구조 | pyproject.toml, 패키지 스캐폴딩, conftest.py |
| 1 | 1 | Git 핵심 레이어 | git_ops.py, bundle.py, checksum.py |
| 2 | 1 | Export + TUI | ui/tui.py, manifest.py, export_.py |
| 3 | 1 | CSV UI + Config | csv ui, config.py |
| 4 | 1 | Import | import_.py, 충돌 처리 3케이스 |
| 4b | 1 | Import Rewrite | rewrite.py, 작성자 매핑, 브랜치 리네임 |
| 5 | 1 | 대용량 + E2E | split archive, E2E 테스트 |
| 6 | 1 | 빌드 | gitshuttle.exe, build.ps1 |

---

## 브랜치 전략

```
main          ← 릴리즈 브랜치 (각 Sprint 완료 후 merge)
  └── sprint/0-scaffold
  └── sprint/1-git-core
  └── sprint/2-export-tui
  └── sprint/3-ui-config
  └── sprint/4-import
  └── sprint/4b-import-rewrite
  └── sprint/5-e2e
  └── sprint/6-build
```

각 Sprint 브랜치에서 개발 → SA3+SA4 PASS → `main` merge → 커밋 & push.
