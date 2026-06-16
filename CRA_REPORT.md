# CRA Report — GitShuttle

> **작성 가이드**  
> 이 문서는 GitShuttle 프로젝트의 기술적 성과를 분석합니다.  
> 1부: 프로젝트 개요 및 배경·기여 효과  
> 2부: Agents / TDD / Clean Code / Refactoring / SOLID / Mock 관점의 핵심 사례

---

## 1부 — 프로젝트 개요

### 제목

**GitShuttle — 망분리 환경 Git 히스토리 이전 CLI 도구**

---

### 배경

기업의 AI 도입이 빨라지면서 새로운 개발 흐름이 생겨나고 있다.

```
[외부망]  개발자 + AI 코딩 도구 (GitHub Copilot, Claude, ChatGPT)
            ↓   코드 작성·리뷰·개선
[분리]    보안 정책상 인터넷 차단 (Air-Gap)
            ↓   USB, 망간 파일 서버
[내부망]  실제 서비스 Git 서버 (사내 GitHub / GitLab)
```

**문제:** 외부망에서 AI와 협업해 만든 코드를 내부망으로 옮길 때, 단순 소스 파일 복사는 커밋 히스토리를 잃는다.  
커밋 메시지, 작성자, AI가 제안한 변경 이유, 리뷰 코멘트 — 모두 사라진다.

**GitShuttle이 해결하는 것:** git bundle 포맷으로 커밋 히스토리 전체를 압축·검증·이전한다.
부분 증분 이전은 hidden 원본 기준점으로 이어가고, 기존 main을 보존해야 하는 상황은 별도 migration 브랜치로 import한 뒤 Git merge로 합친다.

---

### 기여 효과

#### 핵심: 분리된 GitHub 인스턴스 간 히스토리 보존 이전

| 항목 | 단순 파일 복사 | GitShuttle |
|------|:---:|:---:|
| 커밋 메시지 보존 | ❌ | ✅ |
| 작성자·날짜 보존 | ❌ | ✅ |
| AI 기여 이력 추적 | ❌ | ✅ |
| 파일 무결성 검증 | ❌ | ✅ SHA-256 |
| 중복 반입 방지 | ❌ | ✅ |
| Python 없는 환경 | ❌ | ✅ .exe 배포 |

#### AI 도입 맥락에서의 구체적 효과

1. **AI 기여 추적 가능** — 외부망에서 AI와 페어 프로그래밍으로 작성한 커밋이 내부망 Git에도 원본 형태로 남는다. "이 코드가 왜 이렇게 바뀌었는지"를 내부망에서도 `git log`로 확인할 수 있다.

2. **점진적 반입(증분 업데이트)** — 매일 작업 후 그날의 커밋만 골라 bundle로 만들어 전달할 수 있다. 이미 반입된 커밋은 자동으로 건너뛴다.

3. **보안 감사 대응** — `_manifest.txt`에 커밋 목록이 요약되어 반출입 심사 자료로 활용할 수 있다. SHA-256 체크섬으로 USB 이동 중 변조 여부를 자동 검증한다.

4. **망분리 GitHub 이전 흐름 지원**
   - 외부망 GitHub(Public/External) → USB → 내부망 GitHub(On-prem/Private)
   - 네트워크 직접 연결 없이 bundle 파일과 checksum으로 이력 이전

5. **운영 방식 단순화**
   - `bundle`: 전체 이력·부모 관계·Git object 중심 이전. 원본 구조 보존에 적합하다.
   - `migration branch + merge`: 기존 main 위에 바로 덮지 않고 별도 브랜치에 가져온 뒤, Git의 표준 merge 절차로 검토·충돌 해결한다.

---

## 2부 — 기술 사례 분석

---

### 1. Agents 사용 사례

**제목:** 4-SubAgent TDD Harness — SA1→SA2→(SA3‖SA4) 순차·병렬 오케스트레이션

**설명:**  
모든 Sprint를 4개의 전문 SubAgent로 구성된 Harness로 실행했다.  
SA1(문서 검증)이 FAIL이면 구현을 진행하지 않는 게이트 역할을 하며,  
SA3·SA4는 단일 메시지로 동시 실행해 검증 시간을 단축했다.

**구조 사례 — `.claude/agents/` 정의:**

```
.claude/agents/
├── subagent1-doc-verify.md      # PRD↔README↔CLAUDE.md 정합성 검증
├── subagent2-ai-action.md       # TDD 구현 (RED→GREEN→REFACTOR)
├── subagent3-test-verify.md     # pytest 실행 + 회귀 확인
└── subagent4-compliance-verify.md  # 인코딩·네트워크·PEP8 규약 검사
```

**실행 흐름:**
```
Sprint N 시작
  │
  ├─ Agent(SA1)  ← 문서 정합성 PASS 여부 확인
  │     └─ FAIL → 구현 중단, 문서 수정 후 재실행
  │
  ├─ Agent(SA2)  ← TDD 구현 (SA1 PASS 후에만)
  │
  └─ 단일 메시지로 병렬 실행 ──────────────────┐
       Agent(SA3) pytest 106개 PASS 확인        │
       Agent(SA4) flake8·encoding 규약 확인    ─┘
              └─ 둘 다 PASS → 커밋
```

**최근 정리 작업에서 확인한 검토 사례:**
```
tests/test_import.py: unused helper import 제거
tests/test_cli.py: 제거된 옵션 회귀 테스트의 과도한 문자열 매칭 수정
gitshuttle/config.py: 사용하지 않는 설정 API 제거 후 import 설정 파서 유지
```
→ SA2 결과를 SA4가 독립적으로 재검증해 현재 기능과 무관한 코드를 제거했다.

---

### 2. TDD

**제목:** RED → GREEN → REFACTOR — 7 Sprint 연속 테스트 선행 개발

**설명:**  
모든 Sprint에서 구현 파일보다 테스트 파일을 먼저 작성했다.  
Sprint 4(Import) 기준으로 테스트가 ImportError로 실패(RED)한 뒤,  
구현이 완성되면서 7개 모두 통과(GREEN)하는 사이클을 지켰다.

**사례 — `test_import.py` 핵심 3개 테스트:**

```python
# RED: import_.py 미존재 → ImportError
# GREEN: run_import() 구현 완료 후 통과

def test_import_creates_commits_in_target(two_git_repos, tmp_path):
    """export → import 후 타겟 레포 커밋 수가 증가해야 한다."""
    bundle_path = _export_repo(source, tmp_path)
    before_count = len(get_commits(target))

    result = run_import(bundle_path, target)

    assert result.imported >= 1
    assert len(get_commits(target)) > before_count   # 실제 반영 확인


def test_import_abort_on_conflict(two_git_repos, tmp_path):
    """abort 모드에서 중복 커밋 발견 시 ImportConflictError 발생."""
    run_import(bundle_path, target, on_conflict="skip")   # 1차 성공

    with pytest.raises(ImportConflictError):
        run_import(bundle_path, target, on_conflict="abort")  # 2차 중단


def test_import_checksum_mismatch_raises(tmp_path):
    """sha256 불일치 시 ChecksumError + 재export 안내 포함."""
    sha256_path.write_text("0000...  test.bundle", encoding='utf-8')

    with pytest.raises(ChecksumError) as exc_info:
        run_import(bundle_path, fake_repo, sha256_path=sha256_path)

    assert "gitshuttle export" in str(exc_info.value)  # 안내 메시지 검증
```

**Sprint별 테스트 누적:**
```
Sprint 0  →   6 passed
Sprint 1  →  27 passed
Sprint 2  →  39 passed
Sprint 3  →  64 passed
Sprint 4  →  71 passed   ← import_.py
Sprint 5  →  79 passed
Sprint 6  →  85 passed
최종 정리 → 106 passed  (0 failed)
기능 보강 → 145 collected  (hidden refs, TUI 단축키, full-branch export, bundle-only CLI 리팩토링 포함)
```

**최근 TDD 사례 — bundle-only CLI 단순화:**

```python
def test_export_rejects_removed_format_option(tmp_path):
    """export는 bundle 전용이므로 --format 옵션을 제공하지 않는다."""
    result = runner.invoke(app, [
        "export",
        "--repo", str(repo_dir),
        "--format", "bundle",
        "--output", str(tmp_path),
    ])

    assert result.exit_code == 2
    assert "No such option: --format" in result.output


def test_import_rejects_removed_mode_option(tmp_path):
    """import는 bundle 전용이므로 --mode 옵션을 제공하지 않는다."""
    result = runner.invoke(app, [
        "import",
        "--file", str(bundle_path),
        "--repo", str(repo_dir),
        "--mode", "bundle",
    ])

    assert result.exit_code == 2
    assert "No such option: --mode" in result.output
```

**의미:**
전송 방식을 bundle 하나로 줄이면서 사용자가 오래된 옵션을 입력했을 때 조용히 다른 동작을 하지 않도록 회귀 테스트를 먼저 고정했다.
CLI 계약이 단순해졌고, 문서·테스트·구현이 같은 방향을 바라보게 됐다.

---

### 3. Clean Code

**제목:** 단일 책임 함수 분리 + 명시적 예외 계층 — `import_.py`

**설명:**  
`run_import()` 하나가 검증·탐색·반입·병합·집계를 모두 처리하지 않고,  
각 단계를 이름으로 역할이 명확한 내부 함수로 분리했다.  
예외도 도메인별로 분리해 호출자가 원인을 정확히 파악할 수 있게 했다.

**사례 — 함수 분리:**

```python
# 각 함수가 하나의 책임만 가짐

def _verify_checksum(bundle_path, sha256_path) -> None:
    """SHA-256 검증. 불일치 시 ChecksumError."""

def _get_bundle_commits(bundle_path) -> list[str]:
    """bundle의 tip 해시 목록 반환 (중복 감지용)."""

def _unbundle(bundle_path, repo_path) -> list[str]:
    """git bundle unbundle 실행 → objects 추가 + tip 해시 반환."""

def _merge_tip(repo_path, tip_hash) -> None:
    """tip을 현재 브랜치에 병합 (빈 repo / ff / no-ff 분기)."""

def _get_existing_hashes(repo_path) -> set[str]:
    """target repo의 전체 커밋 해시 집합 반환."""
```

**사례 — 예외 계층:**

```python
class ChecksumError(Exception):
    """SHA-256 체크섬 불일치."""

class ImportConflictError(Exception):
    """--on-conflict abort 상황에서 충돌 발견 시."""

# 호출자(cli.py)에서 원인별 분기 처리
try:
    result = run_import(bundle_path, repo_path, on_conflict=on_conflict)
except ChecksumError as e:
    typer.echo(f"[오류] {e}", err=True)     # 파일 손상 → 재export 안내
except ImportConflictError as e:
    typer.echo(f"[중단] {e}", err=True)     # 충돌 → 옵션 변경 안내
except (FileNotFoundError, ValueError) as e:
    typer.echo(f"[오류] {e}", err=True)
```

**사례 — ImportResult 데이터클래스:**

```python
@dataclass
class ImportResult:
    imported: int   # 실제 새로 반입된 커밋 수
    skipped: int    # 이미 존재해 건너뛴 커밋 수
    total: int      # imported + skipped

# 실행 결과 출력
typer.echo(f"  imported : {result.imported}개")
typer.echo(f"  skipped  : {result.skipped}개")
typer.echo(f"  total    : {result.total}개")
```

---

### 4. Refactoring

**제목:** `git remote fetch` → `git bundle unbundle` — 근본 원인 진단 후 구조 교체

**설명:**  
Import 구현 초기에 `git remote add + git fetch` 방식을 사용했으나,  
테스트 2개가 통과하지 못했다. 단순 수정이 아니라 근본 원인을 추적해  
방식 자체를 교체했다.

**문제 발견 과정:**

```
증상: run_import()가 예외 없이 ImportResult(imported=2)를 반환하지만
      타겟 레포의 실제 커밋 수는 변하지 않음

원인 추적:
  create_bundle() → refs/gitshuttle/tmp_abc1234 (커스텀 ref 네임스페이스)
        ↓
  git fetch <remote>의 기본 refspec = refs/heads/* 만 매핑
        ↓
  커스텀 ref는 fetch 대상에서 제외 → FETCH_HEAD 빈 파일 생성
        ↓
  _merge_fetch_head()가 FETCH_HEAD 읽음 → 내용 없음 → 조용히 return
        ↓
  merge 미실행 → 커밋 수 변화 없음
```

**Refactoring 전 (문제 있는 구조):**

```python
# 기본 refspec이 refs/gitshuttle/* 를 가져오지 못함
remote_name = f"shuttle_tmp_{uuid.uuid4().hex[:8]}"
run_git(["remote", "add", remote_name, str(bundle_path)], cwd=repo_path)
run_git(["fetch", remote_name], cwd=repo_path)          # FETCH_HEAD 비어있음
# ...
_merge_fetch_head(repo_path)                              # 아무것도 안 함
```

**Refactoring 후 (교체된 구조):**

```python
# git bundle unbundle: 커스텀 ref 포함 전체 처리 + tip 해시 stdout 출력
tip_hashes = _unbundle(bundle_path, repo_path)   # 직접 objects 추가

for tip_hash in tip_hashes:
    _merge_tip(repo_path, tip_hash)               # 해시로 직접 merge
```

**추가 Refactoring — ImportResult.total 정확도 개선:**

```python
# Before: _get_bundle_commits()가 prerequisites 있는 bundle에서 tip 1개만 반환
#         → total = 1 (실제 10개인데 잘못 집계)
total = len(bundle_commits)   # 부정확

# After: unbundle 전후 해시 집합 비교 → 실제 추가된 수 정확히 집계
existing_before = _get_existing_hashes(repo_path)
tip_hashes = _unbundle(bundle_path, repo_path)
for tip_hash in tip_hashes:
    _merge_tip(repo_path, tip_hash)
existing_after = _get_existing_hashes(repo_path)

imported = len(existing_after - existing_before)  # 정확
total    = imported + skipped
```

**결과 — 테스트 통과 전후:**

```
Before refactoring:
  test_import_creates_commits_in_target  FAILED  assert 1 > 1
  test_import_abort_on_conflict          FAILED  DID NOT RAISE

After refactoring:
  test_import_creates_commits_in_target  PASSED
  test_import_abort_on_conflict          PASSED
  (전체 7/7 PASSED)
```

#### 추가 Refactoring — bundle-only 이력 이전으로 단순화

**배경:**
작성자·날짜 rewrite 후 최근 일부 커밋만 bundle로 가져오려면 대상 repo에 원본 부모 SHA가 있어야 한다.
최신 구현은 `refs/gitshuttle/original/...` hidden 기준점으로 이를 해결한다.
기존 main이 이미 독자적으로 수정된 경우에는 대상 main에 직접 반영하지 않고 migration 브랜치에 import한 뒤 Git merge로 합치는 흐름을 권장한다.

**설계 선택:**

```
bundle import
  - 원본 Git object와 부모 관계 중심
  - hidden 기준점으로 부분 bundle prerequisite 해결
  - 이력 구조 보존에 적합

migration branch + merge
  - 기존 main과 독립된 브랜치에 이력 반입
  - Git merge로 차이 검토 및 충돌 해결
  - 불필요한 별도 전송 포맷 없이 Git 표준 동작 사용
```

**왜 전송 경로를 줄였나:**
GitShuttle의 핵심 가치는 커밋 이력과 Git object graph를 보존하는 것이다.
별도 diff 기반 전송 경로는 사용법과 오류 원인을 늘리고, bundle 기반 증분 기준점·브랜치 merge 흐름과 역할이 겹쳤다.
따라서 export는 항상 bundle을 만들고, import는 bundle 검증·rewrite·target branch checkout/reset 흐름만 유지하도록 단순화했다.

**성능 관점:**
불필요한 포맷 분기를 제거하면서 CLI 옵션 검증, export 결과 출력, import 경로 판단이 줄었다.
성능 개선은 bundle 경로에 집중한다.
`--recent N`은 최신 N개만 조회·선택하고, `--full-branch`는 현재/지정 브랜치 tip 기준 전체 이력을 TUI 없이 self-contained bundle로 만든다.
고급 선택 흐름에서는 `--bundle-scope full`로 선택 tip까지 전체 이력을 포함해 prerequisite 없는 bundle을 만들 수 있다.
CLI 명령 함수는 경로 해석, 선택 UI, 결과 출력 helper로 분리해 기능 변경 없이 읽기성과 테스트 고정성을 높였다.
따라서 현재 권장 기준은 다음과 같다.

| 상황 | 권장 방식 |
|------|-----------|
| 전체 이력 이전, 원본 구조 보존 | `bundle`, 선택 없이 진행 시 `--full-branch` |
| hidden 기준점 기반의 증분 이전 | `bundle` |
| 기존 main 보존 후 검토 반영 | migration 브랜치 import 후 Git merge |
| 많은 커밋을 한 번에 이동 | 대체로 `bundle` 우선 검토 |
| 최신 몇 개 커밋만 이동 | `--recent N`, prerequisite 회피 필요 시 `--bundle-scope full` |

---

### 5. SOLID 원칙 관점

**제목:** Git 히스토리 이전 파이프라인에 적용된 실용적 SOLID

**설명:**  
GitShuttle은 대규모 객체지향 계층을 가진 프로젝트는 아니지만, 핵심 파이프라인을 작은 함수와 명확한 경계로 나누면서 SOLID의 일부 원칙을 실용적으로 적용했다.  
특히 단일 책임 원칙(SRP), 개방-폐쇄 원칙(OCP), 인터페이스 분리 원칙(ISP), 의존성 역전 관점(DIP)이 코드 구조에서 확인된다.

#### SRP — Single Responsibility Principle

**사례:** `run_import()`는 전체 흐름을 조율하고, 실제 책임은 작은 내부 함수로 분리한다.

```python
def _verify_checksum(bundle_path, sha256_path) -> None:
    """SHA-256 검증."""

def _get_existing_hashes(repo_path: Path) -> set[str]:
    """target repo의 전체 커밋 해시 집합 반환."""

def _unbundle(bundle_path: Path, repo_path: Path) -> list[str]:
    """bundle objects 추가 + tip 해시 반환."""

def _merge_tip(repo_path: Path, tip_hash: str) -> None:
    """tip 해시를 현재 브랜치에 병합."""
```

**분석:**  
체크섬 검증, 중복 감지, bundle 반입, merge 처리가 한 함수 안에 뒤섞이지 않는다.  
이 덕분에 `bundle 검증 실패`, `fast-import 실패`, `중복 커밋 처리` 같은 문제를 각각 독립적으로 수정하고 테스트할 수 있다.

#### OCP — Open/Closed Principle

**사례:** `rewrite.py`는 author, branch, timestamp 재작성을 독립 함수로 나누고 `apply_rewrites()`에서 조합한다.

```python
def apply_rewrites(
    stream: str,
    author_map: dict,
    target_branch: str,
    timestamp_mode: str,
    from_dt: Optional[datetime] = None,
) -> tuple[str, list[str]]:
    stream, warnings = rewrite_authors(stream, author_map)
    stream = rewrite_branch_ref(stream, target_branch)
    stream = rewrite_timestamps(stream, mode=timestamp_mode, from_dt=from_dt)
    return stream, warnings
```

**분석:**  
새로운 rewrite 규칙이 필요해도 기존 `rewrite_authors()`나 `rewrite_branch_ref()`를 직접 깨뜨릴 필요가 적다.  
예를 들어 커밋 메시지 prefix 추가, 특정 파일 경로 rewrite 같은 요구가 생기면 새 함수를 만들고 `apply_rewrites()`에 한 단계로 추가할 수 있다.

**확장 사례:**
전체 브랜치 이전 요구는 별도 전송 포맷을 만들지 않고 bundle 경로의 옵션으로 흡수했다.

```python
result = run_export(
    repo_path=repo_path,
    branch=branch,
    output_dir=output_dir,
    commits=selected_commits,
    bundle_scope=bundle_scope,
)
```

핵심 export 동작은 bundle 생성으로 닫혀 있고, `--recent`, `--full-branch`, `--bundle-scope full` 같은 선택 범위만 열려 있다.

#### ISP — Interface Segregation Principle

**사례:** CLI는 복잡한 내부 구현을 직접 알지 않고, 좁은 API와 결과 객체만 사용한다.

```python
result = run_import(
    bundle_path=bundle_path,
    repo_path=repo_path,
    on_conflict=on_conflict,
    author_map_path=effective_author_map,
    target_branch=target_branch,
    timestamp_mode=effective_timestamp,
)

typer.echo(f"  imported : {result.imported}개")
typer.echo(f"  skipped  : {result.skipped}개")
typer.echo(f"  total    : {result.total}개")
```

**분석:**  
CLI 레이어는 `git bundle`, `fast-export`, `fast-import`, SHA-256 계산 방식까지 알 필요가 없다.  
`ImportResult`의 `imported`, `skipped`, `total`, `warnings`만 사용하므로 호출자 관점의 인터페이스가 작고 명확하다.

**최근 사례 — import 결과 인터페이스 유지:**

```python
result = run_import(
    bundle_path=bundle_path,
    repo_path=repo_path,
    on_conflict=on_conflict,
    author_map_path=effective_author_map,
    target_branch=target_branch,
    timestamp_mode=effective_timestamp,
)
```

CLI는 checksum 검증, hidden ref 보관, fast-import, checkout/reset 같은 세부 구현을 몰라도 동일한 `ImportResult` 출력 로직을 사용할 수 있다.

#### DIP — Dependency Inversion Principle 관점

**사례:** 상위 레이어인 `cli.py`는 Git 명령 실행 세부사항에 직접 의존하지 않고 `run_export()`, `run_import()` 같은 유스케이스 함수에 의존한다.

```python
# cli.py
from gitshuttle.import_ import run_import, ChecksumError, ImportConflictError

# import_.py 내부에서만 subprocess, git bundle, fast-import 세부 구현 처리
```

**분석:**  
완전한 DI 컨테이너 구조는 아니지만, 사용자 인터페이스와 Git 처리 세부 구현이 분리되어 있다.  
테스트에서도 이 경계가 활용되어 `cli.py`는 `run_export()`와 `run_import()`를 monkeypatch하고, 실제 Git 동작은 별도 임시 repo 기반 통합 테스트로 검증한다.

**적용하지 않은 원칙 — LSP:**  
이 프로젝트는 상속 기반 다형성보다 함수 조합과 데이터클래스를 중심으로 구성되어 있어 LSP(Liskov Substitution Principle)를 평가할 만한 클래스 계층이 거의 없다.  
이는 SOLID 미준수라기보다, 문제 크기에 맞게 불필요한 상속 구조를 만들지 않은 설계 선택에 가깝다.

---

### 6. Mock 관점

**제목:** CLI 계약과 실제 Git 동작을 분리한 테스트 전략

**설명:**  
GitShuttle은 CLI 옵션 전달처럼 빠르게 검증할 수 있는 부분은 `monkeypatch`, `CliRunner`로 격리한다.
반면 bundle 생성·검증·import처럼 Git object가 실제로 움직이는 부분은 임시 Git repo를 만들어 통합 테스트로 확인한다.

#### 사례 1 — CLI의 export/import API 호출 격리

`tests/test_cli.py`는 실제 bundle 생성 없이 `run_export()`를 monkeypatch해 CLI 옵션이 내부 API로 전달되는지 검증한다.

```python
def fake_run_export(repo_path, commits, output_dir, branch, bundle_scope="range"):
    captured["repo_path"] = repo_path
    captured["bundle_scope"] = bundle_scope
    return ExportResult(
        bundle=output_dir / "test.bundle",
        sha256=output_dir / "test.bundle.sha256",
        manifest=output_dir / "test_manifest.txt",
    )

monkeypatch.setattr(export_module, "run_export", fake_run_export)
```

**효과:**  
CLI 테스트가 Git bundle 생성 비용이나 로컬 Git 상태에 흔들리지 않는다.
`--repo`, `--recent`, `--full-branch`, `--bundle-scope` 같은 옵션 계약을 빠르게 검증할 수 있다.

#### 사례 2 — 실제 Git repo 기반 통합 테스트

`tests/test_import.py`, `tests/test_bundle.py`, `tests/test_e2e.py`는 임시 Git repo를 만들고 실제 `git bundle`, `git fast-export`, `git fast-import` 흐름을 실행한다.

```python
bundle_path = _export_repo(source, tmp_path)
before_count = len(get_commits(target))

result = run_import(bundle_path, target)

assert result.imported >= 1
assert len(get_commits(target)) > before_count
```

**효과:**  
mock으로는 잡기 어려운 Git object prerequisite, fast-import 입력 형식, worktree checkout/reset 문제를 실제 Git 실행으로 잡는다.

#### 사례 3 — rewrite 옵션 전달 monkeypatch

CLI import 테스트는 `run_import()`를 fake 함수로 바꿔 작성자 매핑과 타임스탬프 옵션 전달만 빠르게 확인한다.

```python
def fake_run_import(..., author_map_path=None, timestamp_mode="now"):
    captured["author_map_path"] = author_map_path
    captured["timestamp_mode"] = timestamp_mode
    return ImportResult(imported=1, skipped=0, total=1)
```

**효과:**  
느린 import 파이프라인을 반복 실행하지 않고도 CLI 계약을 고정한다.

#### 사례 4 — CLI 테스트의 monkeypatch

`tests/test_cli.py`는 `run_export()`와 `run_import()`를 fake 함수로 바꿔 CLI 옵션 전달만 검증한다.

```python
def fake_run_import(
    bundle_path,
    repo_path,
    on_conflict="skip",
    sha256_path=None,
    author_map_path=None,
    target_branch=None,
    timestamp_mode="now",
):
    captured["repo_path"] = repo_path
    captured["timestamp_mode"] = timestamp_mode
    return ImportResult(imported=1, skipped=0, total=1)

monkeypatch.setattr(import_module, "run_import", fake_run_import)
```

**효과:**  
CLI 테스트가 실제 bundle 검증이나 fast-import에 의존하지 않는다.  
`--repo`, `--timestamp` 같은 옵션이 내부 API로 정확히 전달되는지 빠르게 확인할 수 있다.

#### 사례 5 — 제거된 CLI 옵션 회귀 검증

`tests/test_cli.py`는 제거된 옵션이 조용히 받아들여지지 않는지 검증한다.
이 테스트는 실제 Git 작업 없이 CLI 계약만 빠르게 고정한다.

```python
result = runner.invoke(app, [
    "import",
    "--file", str(bundle_path),
    "--repo", str(repo_dir),
    "--mode", "bundle",
])

assert result.exit_code == 2
assert "No such option: --mode" in result.output
```

**효과:**
사용자가 예전 명령을 복사해 실행했을 때 현재 CLI가 명확하게 실패하도록 보장한다.
동시에 export/import 경로가 bundle 하나로 유지되는지 빠르게 확인할 수 있다.

#### Mock 사용 시 주의점

Mock은 외부 의존성을 빠르고 안정적으로 격리하지만, 실제 Git 동작과 완전히 같지는 않다.  
그래서 GitShuttle은 mock 테스트만 두지 않고 `test_import.py`, `test_bundle.py`, `test_e2e.py`처럼 실제 임시 Git repo를 만들어 검증하는 테스트도 함께 둔다.

**정리:**  
Mock 테스트는 "명령 호출 방식", "오류 처리", "CLI 옵션 전달"을 빠르게 검증하고, 실제 Git repo 기반 테스트는 bundle 생성·검증·반입의 현실 동작을 보완한다.

---

*GitShuttle · Sprint 0~6 완료 + 기능 보강 · 145 tests collected · hidden refs, full-branch export, bundle-only CLI 리팩토링 포함*
