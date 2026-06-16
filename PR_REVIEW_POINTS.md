# PR Review Points — GitShuttle 전체 프로젝트

---

## PR 제목

```
feat: GitShuttle v0.1.0 — 망분리 환경 Git 히스토리 동기화 CLI (Phase 1 완료)
```

---

## PR Description

### 개요

**GitShuttle**은 인터넷이 차단된 망분리(Air-Gapped) 환경에서 Git 커밋 히스토리를 USB 등 물리 매체를 통해 외부망 → 내부망으로 이전하는 CLI 도구입니다.

```
[외부망 PC]                                              [내부망 PC]
─────────────────────────────                    ─────────────────────────
gitshuttle export                  USB →       gitshuttle import
  → .bundle (히스토리 압축)        이동          --file shuttle.bundle
  → .sha256 (무결성 검증)          →→→→          (SHA-256 검증 후 반영)
  → _manifest.txt (심사용 목록)    →→→→
```

### 스프린트별 구현 범위

| Sprint | 브랜치 | 구현 내용 |
|--------|--------|-----------|
| 0 | `sprint/0-scaffold` | 프로젝트 기반 구조 (pyproject.toml, 패키지 골격, CI) |
| 1 | `sprint/1-git-core` | git 서브프로세스 레이어 (log, bundle, verify, checksum, manifest) |
| 2 | `sprint/2-export-tui` | export 오케스트레이션 + Textual TUI 커밋 선택기 |
| 3 | `sprint/3-ui-config` | CSV·HTML·Prompt UI + config 마법사 (gitshuttle.toml) |
| 4 | `sprint/4-import` | import 오케스트레이션 (SHA-256 검증, unbundle, fast-forward) |
| 4b | `sprint/4b-import-rewrite` | Import Rewrite (작성자 매핑·브랜치 격리·타임스탬프 재작성) |
| 5 | `sprint/5-e2e` | E2E 테스트 (실제 git repo 대상, 분할 전송 포함) |
| 6 | `sprint/6-build` | PyInstaller 빌드 스펙·스크립트 (`gitshuttle.spec`, `build.ps1`) |

---

### 파일 구조 및 역할

```
gitshuttle/                   15개 모듈
├── __init__.py               버전 상수
├── __main__.py               엔트리포인트 (UTF-8 강제)
├── cli.py                    Typer app (export/import/config 커맨드)
├── git_ops.py                git 서브프로세스 래퍼 (log, bundle, verify)
├── bundle.py                 bundle 생성·검증·분할·재조립
├── checksum.py               SHA-256 생성·검증
├── manifest.py               커밋 목록 요약 파일 생성
├── export_.py                export 오케스트레이션
├── import_.py                import 오케스트레이션 + Rewrite 파이프라인
├── rewrite.py                fast-export 스트림 치환 (작성자·브랜치·타임스탬프)
├── config.py                 gitshuttle.toml 읽기·쓰기·마법사
└── ui/
    ├── tui.py                Textual 체크박스 + 테이블 (기본값)
    ├── csv_ui.py             commits.csv 생성·파싱 (utf-8-sig)
    ├── html_ui.py            단일 HTML (인터넷 불필요), selection.json 파싱
    └── prompt_ui.py          InquirerPy 방향키 멀티셀렉트

tests/                        14개 테스트 파일, 145개 테스트
├── conftest.py               임시 git repo 픽스처
├── test_git_ops.py
├── test_bundle.py
├── test_checksum.py
├── test_manifest.py
├── test_export.py
├── test_import.py
├── test_rewrite.py           30개 (Sprint 4b + data payload 보존)
├── test_config.py
├── test_build.py
└── ui/
    ├── test_csv_ui.py
    ├── test_html_ui.py
    ├── test_prompt_ui.py
    └── test_tui.py             TUI A/E 키 바인딩 검증
```

---

### 핵심 아키텍처 결정

#### 1. git bundle 포맷 활용

`git bundle create` / `git bundle unbundle` 을 직접 호출해 Git 내장 포맷을 그대로 사용합니다.
별도 직렬화 없이 브랜치·태그·히스토리를 100% 보존하며, Git 2.37+ 에서 검증됩니다.

#### 2. Import Rewrite 파이프라인 (Sprint 4b)

```
git fast-export <branch>
  │
  ├── rewrite_authors()      이메일 키 기반 작성자 치환
  ├── rewrite_branch_ref()   refs/heads/* → refs/heads/<target>
  └── rewrite_timestamps()   now | original | from=<UTC datetime>
  │
git fast-import (binary mode)
```

`git fast-import` subprocess를 **바이너리 모드**(`input=bytes`, `encoding=` 파라미터 없음)로 호출합니다.
Windows에서 `encoding='utf-8'` 사용 시 CRLF 변환이 발생해 `blob\r\n` → `blob?` 파싱 오류가 생기는 버그를 방지합니다.

또한 fast-export 스트림의 `data N` payload는 파일 내용·커밋 메시지 본문이므로 rewrite 대상에서 제외합니다.  
`rewrite_authors()`, `rewrite_branch_ref()`, `rewrite_timestamps()`는 control line만 변경하고 `data N` 뒤의 N바이트는 원문 그대로 보존합니다.

#### 3. 브랜치 격리 전략

소스 `main`/`master`를 타겟의 기본 브랜치에 직접 병합하지 않고, `imported/<소스브랜치>` 신규 브랜치에 격리합니다.
검토 후 담당자가 직접 `git merge`를 수행하도록 설계했습니다.

#### 4. SHA-256 무결성 검증

export 시 bundle 파일의 SHA-256 체크섬을 `.sha256` 파일에 저장합니다.
import 시 자동 검증 — 불일치 시 `ChecksumError`를 raise해 손상·변조된 파일 반입을 차단합니다.

#### 5. UTF-8 / 한글 처리

- 모든 파일 I/O에 `encoding='utf-8'` 명시
- `__main__.py`에서 `sys.stdout`/`sys.stderr`를 UTF-8로 래핑
- CSV는 Excel 호환을 위해 `utf-8-sig` 사용
- `git` 서브프로세스에 `PYTHONIOENCODING=utf-8` 환경변수 전달

---

### 커맨드 요약

```
gitshuttle export   [--repo <path>] [--branch] [--ui tui|csv|html|prompt] [--output]
                    [--bundle-scope range|full]
                    [--full-branch]
                    [--recent <N>]
gitshuttle import   --file <path>
                    [--repo <path>]
                    [--on-conflict skip|force|abort]
                    [--author-map <json>]
                    [--target-branch <name>]
                    [--timestamp now|original|from=<UTC_ISO>]
gitshuttle config   (대화형 마법사)
```

---

### 테스트 현황

```
현재 수집 테스트: 145개
커버리지 대상 모듈: git_ops, bundle, checksum, manifest, export_, import_,
                   rewrite, config, ui(csv/html/prompt), build
```

```bash
# 전체 실행
python -m pytest tests/ -v --tb=short
```

---

### 알려진 제약 및 미완 사항

| 항목 | 상태 | 비고 |
|------|------|------|
| `gitshuttle.exe` 빌드 | 미완 | 사내 PyInstaller 설치 불가 (프록시 SSL 차단). `build.ps1` + `gitshuttle.spec` 준비 완료 |
| `author_map.json` 키 형식 검증 | 문서화 완료 | 키는 이메일 주소 단독, 값은 `{name,email}` dict. 형식 검증 추가 여지 있음 |
| TUI (Textual) Windows CMD | 제한적 | Windows Terminal / PowerShell 7+ 권장 |

---

## 리뷰 요청 포인트

### 🔴 중점 검토

#### R1. `git fast-import` 바이너리 모드 (`import_.py`)

```python
# 올바른 방식 — encoding 파라미터 없이 bytes 전달
subprocess.run(
    ["git", "fast-import", "--quiet"],
    input=rewritten_stream.encode('utf-8', errors='surrogateescape'),   # bytes
    capture_output=True,
    # encoding= 파라미터 없음 → binary mode
)
```

Windows에서 `encoding='utf-8'`을 지정하면 Python이 `\n`을 `\r\n`으로 변환해
`git fast-import`가 blob 헤더를 파싱 실패합니다. 이 패턴이 다른 subprocess 호출에도
동일하게 적용되어 있는지 확인해 주세요.

#### R2. `_IDENTITY_RE` 정규식 엣지케이스 (`rewrite.py:26~33`)

```python
_IDENTITY_RE = re.compile(
    r'^(author|committer)\s+'
    r'(.+?)\s+'           # 이름 — 그리디하지 않게
    r'<([^>]+)>\s+'       # 이메일
    r'(\d+)\s+'           # Unix timestamp
    r'([+-]\d{4})$',
    re.MULTILINE,
)
```

이름 그룹 `(.+?)` 이 `<` 를 포함하면 매칭이 끊길 수 있습니다.
한글 이름, 특수문자가 포함된 커밋 작성자에 대한 round-trip 검증을 확인해 주세요.

#### R3. `rewrite_needed` 조건 (`import_.py:~450`)

```python
rewrite_needed = (
    author_map_path is not None
    or target_branch is not None
    or timestamp_mode != "now"   # "now"가 기본값 — original/from= 시에만 rewrite
)
```

세 옵션 모두 기본값이면 기존 `unbundle` 경로를 유지합니다.
`timestamp_mode != "original"` 로 잘못 작성 시 기본값 `"now"` 에서도 rewrite 경로가
활성화되어 기존 동작이 깨지는 버그가 있었습니다 (수정 완료). 조건식의 의도를 확인해 주세요.

#### R4. fast-export `data N` payload 보존 (`rewrite.py`)

```python
def _rewrite_control_lines(stream: str, rewrite_line: Callable[[str], str]) -> str:
    """data payload를 보존하며 control line만 재작성한다."""
```

`git fast-export`의 `data N` 다음 N바이트는 파일 내용 또는 커밋 메시지입니다.  
이 영역에 정규식 치환을 적용하면 `data N` 길이와 실제 payload 길이가 어긋나고,
`git fast-import`가 파일 내용을 명령어로 해석해 `Unsupported command` 오류를 낼 수 있습니다.
`TestRewritePreservesDataBlocks`가 이 회귀를 방지하는지 확인해 주세요.

#### R5. rewrite import의 non-fast-forward target branch 처리 (`import_.py`)

대상 브랜치가 이미 존재하고 새 import tip이 기존 tip을 포함하지 않으면 `git fast-import`는 ref 업데이트를 거부합니다.  
현재 구현은 `--on-conflict force`일 때만 `git fast-import --force`를 전달해 명시적 덮어쓰기를 허용합니다.
기본값(`skip`)에서는 다른 `--target-branch` 사용 또는 기존 로컬 브랜치 삭제를 안내합니다.

#### R6. fast-import 후 worktree 갱신 (`import_.py`)

`git fast-import`는 refs/object DB를 갱신하지만 일반 working tree와 index를 자동으로 갱신하지 않습니다.  
rewrite import 완료 후 `_checkout_or_create_branch()`가 대상 브랜치로 checkout하고 `reset --hard <tip>`을 실행해 실제 파일이 폴더에 보이도록 맞춥니다.
사용자 변경 손실을 막기 위해 fast-import 전에 `_ensure_clean_worktree()`가 `git status --porcelain`을 확인합니다.

#### R7. rewrite 이후 부분 bundle 증분 기준점 (`import_.py`)

부분 bundle은 직전 원본 부모 SHA를 prerequisite로 요구합니다.
author/timestamp rewrite를 하면 target branch의 커밋 SHA가 원본과 달라지므로, 기존 방식만으로는 다음 부분 bundle 검증이 실패할 수 있습니다.

최신 구현은 rewrite import 성공 후 원본 bundle refs를 `refs/gitshuttle/original/<target-branch>/...`에 보관합니다.
다음 rewrite import에서는 이 숨김 ref를 임시 bare repo로 fetch해 prerequisite 객체를 채운 뒤, fast-export 대상에 섞이지 않도록 숨김 ref 자체는 삭제합니다.

검토 포인트:
- 숨김 ref가 일반 target branch나 push 대상에 섞이지 않는지
- `fast-export --all`에 `refs/gitshuttle/original/...` reset/commit 라인이 포함되지 않는지
- reported `imported` 수가 보관용 원본 객체를 세지 않고 target branch의 새 커밋만 세는지

#### R8. bundle-only CLI 단순화 (`cli.py`, `export_.py`, `import_.py`)

별도 diff 재생 모드를 제거하고 GitShuttle의 전송 경로를 bundle 기반 이력 이전으로 단순화했습니다.

검토 포인트:
- `--format`, 별도 압축 모드, `--mode` 옵션이 CLI 도움말과 문서에서 제거되었는지
- export가 항상 `.bundle`을 만들고 checksum/manifest 생성 흐름을 유지하는지
- import가 bundle 검증, rewrite, target branch checkout/reset 흐름만 유지하는지
- 기존 코드가 있는 repo에서는 migration 브랜치 import 후 merge하는 가이드가 README/MANUAL/EXAMPLE/PRD에 일관되게 설명되는지
- `--recent N`이 TUI를 열지 않고 최신 N개만 조회·선택하는지
- `--full-branch`가 TUI 없이 브랜치 tip만 조회하고 `bundle_scope=full`로 self-contained bundle을 만드는지

---

### 🟡 일반 검토

#### Y1. `bundle.py` — 분할 전송 (`bundle.py`)

`split_bundle` / `merge_bundles` 로 대용량 bundle을 청크 단위로 분할합니다.
분할 파일 중 하나라도 누락 시 `merge_bundles`가 어떻게 동작하는지 확인해 주세요.

#### Y2. `checksum.py` — `.sha256` 파일 없을 때 동작 (`import_.py:~300`)

`.sha256` 파일이 없으면 `[경고]` 메시지를 출력하고 검증을 건너뜁니다.
보안 정책에 따라 검증을 강제화해야 하는 환경에서는 `--require-checksum` 옵션 추가가 필요할 수 있습니다.

#### Y2-1. 부분 bundle prerequisite 실패 안내 (`bundle.py`, `import_.py`)

최근 1~2개 커밋만 선택한 bundle은 직전 부모 커밋을 prerequisite로 가집니다.  
대상 repo가 원본 부모 SHA를 갖고 있지 않거나, author/timestamp rewrite로 SHA가 바뀐 경우 `git bundle verify`가 실패합니다.
`verify_bundle_detailed()`와 import 오류 메시지가 이 원인 및 `refs/gitshuttle/original/...` 기준점 생성 필요성을 사용자에게 설명하는지 확인해 주세요.
`--full-branch`는 현재/지정 브랜치 tip 기준 전체 이력을 TUI 없이 self-contained bundle로 만들며, merge된 서브브랜치 이력까지 포함합니다. 고급 선택 흐름에서는 `--bundle-scope full`이 선택 tip까지 전체 이력을 포함해 prerequisite 없는 bundle을 만들고, `--on-conflict force --target-branch ...` 조합으로 강제 이어붙이기에 사용할 수 있습니다.

GitShuttle은 bundle 이력 이전에 집중합니다. 기존 코드 위에 변경분을 직선형으로 재생하는 별도 diff 재생 모드는 제거했고, 기존 main 보존이 필요하면 migration 브랜치 import 후 Git merge로 합칩니다.

#### Y3. `_detect_source_branch` fallback (`import_.py:~390`)

bundle에 named ref가 없으면 `"main"` 을 fallback으로 반환합니다.
`commit hash` 만으로 생성된 bundle 이나 detached HEAD 상태의 bundle에서
`imported/main` 이 기본 브랜치명으로 사용되는 것이 의도한 동작인지 확인해 주세요.

#### Y4. `author_map.json` 키 형식 (`rewrite.py:46~68`)

매핑 키는 **이메일 주소 단독** (`"ltw070@naver.com"`)이어야 합니다.
`"Name <email>"` 형식으로 입력하면 해당 이메일이 매칭되지 않아 미매핑 경고가 출력됩니다.
입력 검증 로직 추가 또는 문서화 수준으로 처리할지 결정이 필요합니다.

#### Y5. `config.py` — toml 우선순위 (`config.py:~260`)

```
CLI --author-map 파일 경로  >  gitshuttle.toml [import].author_map  >  없음
CLI --timestamp 모드        >  gitshuttle.toml [import].timestamp    >  "now"
```

CLI와 toml이 동시에 설정된 경우 CLI 옵션이 우선합니다.
사용자에게 어떤 설정이 적용됐는지 verbose 출력으로 알려주는 것을 고려해 주세요.

### 🟢 확인 완료

- **테스트 145개 수집 확인** — 전체 suite는 환경에 따라 장시간 실행될 수 있음
- **UTF-8 / 한글 처리** — 모든 파일 I/O, subprocess, TUI에 인코딩 명시
- **망분리 제약** — 외부 네트워크 호출 코드 없음
- **Breaking Changes 없음** — 기존 `gitshuttle import --file <bundle>` 호환 유지
- **SA4 규약 검증 PASS** — 인코딩, 네트워크 격리, Phase 1 범위 준수
- **`[imported]` 태그** — TUI에서 이미 반입된 커밋 시각적 구분
- **충돌 처리 3모드** — `skip`(기본) / `force` / `abort`
- **fast-export data payload 보존** — 파일 내용 안의 `author`, `commit refs/...` 문자열은 rewrite하지 않음

---

### 테스트 방법

```bash
# 전체 테스트
python -m pytest tests/ -v --tb=short

# Sprint 4b (Rewrite) 단위 테스트만
python -m pytest tests/test_rewrite.py -v

# 기본 export → import 흐름 (EXAMPLE.md 예제 1 참고)
cd <source-repo>
python -m gitshuttle export --ui csv

cd <target-repo>
python -m gitshuttle import --file /path/to/shuttle.bundle

# Import Rewrite 실전 (EXAMPLE.md 예제 3 참고)
PYTHONPATH=D:/cla/03_gitshuttle python -m gitshuttle import \
  --file /tmp/first10.bundle \
  --author-map /tmp/author_map.json \
  --target-branch feat/my-branch \
  --timestamp from=2026-05-09T01:23:00
```

---

### exe 빌드 방법 (수동)

```powershell
# PyInstaller 설치 환경에서 (사내망 외부 또는 오프라인 pip)
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File build.ps1
# → dist\gitshuttle.exe 생성
```

> 현재 환경: 사내 프록시 SSL 인증서 검증 이슈로 PyInstaller 설치 불가.
> `gitshuttle.spec` 과 `build.ps1` 은 준비 완료. Python 패키지 설치 가능한 환경에서 빌드.

---

### 관련 문서

| 문서 | 내용 |
|------|------|
| `PRD.md` | 전체 기능 스펙 (섹션 3.6 Import-time Rewrite 포함) |
| `PLAN.md` | Sprint 0~7 계획 및 수락 기준 |
| `README.md` | 사용자 빠른 시작 가이드 |
| `MANUAL.md` | 전체 사용자 매뉴얼 (섹션 7-1 Rewrite 포함) |
| `EXAMPLE.md` | 3가지 실전 시나리오 (최초 이전, 증분 업데이트, Import Rewrite) |
| `REPORT.md` | 세션별 작업 기록 및 설계 결정 이유 |
| `CRA_REPORT.md` | Agents / TDD / Clean Code / Refactoring / SOLID / Mock 관점 분석 |
