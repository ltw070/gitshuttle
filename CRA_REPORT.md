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
또한 hidden 기준점을 만들 수 없는 운영 상황에서는 patchset/replay 방식으로 선택 커밋의 변경분을 대상 브랜치 위에 새 커밋으로 재생할 수 있다.

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

4. **망분리 GitHub 양방향 구조 지원**
   - 외부망 GitHub(Public/External) → USB → 내부망 GitHub(On-prem/Private)
   - Phase 2 Direct Sync: 네트워크가 허용될 때 API로 직접 동기화

5. **운영 방식 이원화**
   - `bundle`: 전체 이력·부모 관계·Git object 중심 이전. 원본 구조 보존에 적합하다.
   - `patchset/replay`: 기준점 없이 일부 변경분만 대상 HEAD 위에 재생. 내부 브랜치가 이미 달라진 상황에서 작업자 책임으로 적용하기 쉽다.

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

**SA4가 발견한 실제 위반 사례 (Sprint 7):**
```
tests/test_sync.py:8   F401 'os' imported but unused
tests/test_sync.py:11  F401 'unittest.mock.call' imported but unused
tests/test_sync.py:206 F841 local variable 'result' assigned but never used
```
→ SA2 결과를 SA4가 독립적으로 재검증해 미사용 코드를 자동 제거했다.

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
Sprint 7  → 102 passed
최종 정리 → 106 passed  (0 failed)
기능 보강 → 168 collected  (hidden refs, patchset/replay, TUI 단축키, patchset export 속도 개선 포함)
```

**최근 TDD 사례 — patchset/replay:**

```python
def test_run_replay_import_applies_patchset_with_author_map(tmp_path):
    """patchset을 대상 HEAD 위에 replay하고 author_map을 적용한다."""
    patchset = create_patchset(source, [commits[0]], tmp_path, "feature.patchset")

    result = run_replay_import(
        patchset_path=patchset,
        repo_path=target,
        author_map_path=str(author_map),
        target_branch="main",
        timestamp_mode="original",
    )

    assert result.imported == 1
    assert latest == "feat: replay feature|ltw070 <ltw070@naver.com>"


def test_replay_import_duplicate_head_message_requires_confirmation(tmp_path):
    """대상 HEAD subject와 첫 replay subject가 같으면 확인을 요구한다."""
    with pytest.raises(ValueError):
        run_replay_import(..., confirm_duplicate_message=lambda head, first: False)
```

**의미:**
사용자 요구인 "기준점 없이 작업자 책임으로 cherry-pick 형태로 붙이기"를 구현하기 전에,
patchset 생성·replay 적용·중복 커밋 메시지 확인 조건을 테스트로 먼저 고정했다.

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

#### 추가 Refactoring — bundle 이력 이전과 patchset replay 분리

**배경:**
작성자·날짜 rewrite 후 최근 일부 커밋만 bundle로 가져오려면 대상 repo에 원본 부모 SHA가 있어야 한다.
최신 구현은 `refs/gitshuttle/original/...` hidden 기준점으로 이를 해결하지만, 이미 내부 브랜치가 독자적으로 수정된 경우에는 "원본 이력 mirror"보다 "변경분만 적용"이 더 자연스러운 요구가 생겼다.

**설계 선택:**

```
bundle import
  - 원본 Git object와 부모 관계 중심
  - hidden 기준점으로 부분 bundle prerequisite 해결
  - 이력 구조 보존에 적합

patchset replay
  - 커밋별 binary diff + metadata 저장
  - 대상 HEAD 위에 새 커밋으로 재생
  - 기준점 없이 일부 변경 적용에 적합
```

**왜 기존 bundle 경로에 억지로 넣지 않았나:**
bundle은 Git object graph를 다루고, patchset은 diff replay를 다룬다.
두 방식을 하나의 흐름에 섞으면 "원본 이력 보존"과 "작업자 책임 적용"의 의미가 흐려진다.
그래서 `--format patchset`, `--mode replay`로 별도 모드화했다.

**성능 관점:**
patchset import는 일부 커밋 적용 시 가볍지만, patchset export는 patch 파일을 만들어야 하므로 많은 커밋에서는 bundle보다 느릴 수 있다.
이 병목을 줄이기 위해 metadata는 `git show --no-patch`로 batch 조회하고, parent 정보는 metadata에서 재사용해 `rev-list` 중복 호출을 제거했다.
연속 선형 first-parent 범위는 `git format-patch --stdout` 기반으로 빠르게 만들고, merge나 비연속 선택은 기존 커밋별 diff 방식으로 fallback한다.
CLI에는 `--recent N`을 추가해 최신 N개만 조회·선택하게 했고, `--patchset-compression fast|stored|deflated`로 zip 압축 비용을 조절할 수 있게 했다.
이미 적용된 patch는 skip하고, 같은 경로의 다른 내용 충돌은 복구 안내와 함께 중단하도록 보강했다.
따라서 현재 권장 기준은 다음과 같다.

| 상황 | 권장 방식 |
|------|-----------|
| 전체 이력 이전, 원본 구조 보존 | `bundle` |
| hidden 기준점 기반의 증분 이전 | `bundle` |
| 기준점 없이 내부 브랜치 위에 일부 변경만 적용 | `patchset/replay` |
| 많은 커밋을 한 번에 이동 | 대체로 `bundle` 우선 검토 |
| 최신 몇 개 커밋만 patchset으로 이동 | `--recent N` + 필요 시 `--patchset-compression stored` |

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
patchset/replay는 기존 bundle import 의미를 바꾸지 않고, `patchset.py`와 `import_mode` 분기로 추가했다.

```python
if import_mode == "replay" or (
    import_mode == "auto" and bundle_path.suffix.lower() == ".patchset"
):
    replay_result = run_replay_import(...)
```

기존 bundle import는 그대로 닫혀 있고, replay 기능은 새 모듈로 열려 있다.

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

**최근 사례 — replay 결과도 같은 호출자 인터페이스로 흡수:**

```python
replay_result = run_replay_import(...)
return ImportResult(
    imported=replay_result.imported,
    skipped=replay_result.skipped,
    total=replay_result.total,
    warnings=replay_result.warnings,
)
```

CLI는 bundle import인지 patchset replay인지 세부 구현을 몰라도 동일한 결과 출력 로직을 사용할 수 있다.

#### DIP — Dependency Inversion Principle 관점

**사례:** 상위 레이어인 `cli.py`는 Git 명령 실행 세부사항에 직접 의존하지 않고 `run_export()`, `run_import()` 같은 유스케이스 함수에 의존한다.

```python
# cli.py
from gitshuttle.import_ import run_import, ChecksumError, ImportConflictError

# import_.py 내부에서만 subprocess, git bundle, fast-import 세부 구현 처리
```

**분석:**  
완전한 DI 컨테이너 구조는 아니지만, 사용자 인터페이스와 Git 처리 세부 구현이 분리되어 있다.  
테스트에서도 이 경계가 활용되어 `cli.py`는 `run_import()`를 monkeypatch하고, `sync_.py`는 `subprocess.run`을 mock 처리해 네트워크 없이 검증한다.

**적용하지 않은 원칙 — LSP:**  
이 프로젝트는 상속 기반 다형성보다 함수 조합과 데이터클래스를 중심으로 구성되어 있어 LSP(Liskov Substitution Principle)를 평가할 만한 클래스 계층이 거의 없다.  
이는 SOLID 미준수라기보다, 문제 크기에 맞게 불필요한 상속 구조를 만들지 않은 설계 선택에 가깝다.

---

### 6. Mock 관점

**제목:** 외부 GitHub·Git subprocess를 격리한 테스트 전략

**설명:**  
GitShuttle은 실제 GitHub 접근, 토큰 인증, 네트워크 push처럼 느리고 실패 가능성이 높은 동작을 테스트에서 직접 수행하지 않는다.  
대신 `unittest.mock.patch`, `MagicMock`, `monkeypatch`, `CliRunner`를 사용해 외부 의존성을 격리하고, 코드가 어떤 명령과 옵션을 호출하는지 검증한다.

#### 사례 1 — Direct Sync의 subprocess mock

`tests/test_sync.py`는 `gitshuttle.sync_.subprocess.run`을 mock 처리해 실제 clone/push 없이 Direct Sync 흐름을 검증한다.

```python
with patch("gitshuttle.sync_.subprocess.run") as mock_run:
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    run_sync(
        source_url="https://github.com/org1/repo",
        target_url="https://github.com/org2/repo",
        work_dir=tmp_path,
    )

assert mock_run.call_count >= 1
```

**효과:**  
테스트가 네트워크 상태, GitHub 권한, 토큰 만료 여부에 영향을 받지 않는다.  
CI 환경에서도 안정적으로 실행할 수 있고, 실패 원인이 비즈니스 로직인지 외부 서비스인지 분리된다.

#### 사례 2 — subprocess 호출 옵션 검증

동기화 테스트는 mock 호출 기록을 검사해 모든 Git 명령이 UTF-8 인코딩과 안전한 환경변수를 사용하는지 확인한다.

```python
for c in mock_run.call_args_list:
    kwargs = c.kwargs if c.kwargs else {}
    assert kwargs.get("encoding") == "utf-8"

    env = kwargs.get("env")
    if env is not None:
        assert env.get("PYTHONIOENCODING") == "utf-8"
```

**효과:**  
실제 Git 명령을 실행하지 않아도 "명령을 어떤 방식으로 호출하는가"를 검증할 수 있다.  
Windows 한글 경로, 콘솔 인코딩, 망분리 환경에서 자주 발생하는 문자 깨짐 위험을 테스트 레벨에서 줄인다.

#### 사례 3 — 보안 관점 mock: 토큰 노출 방지

실패하는 subprocess 결과를 mock으로 만들고, 예외 메시지에 토큰이 포함되지 않는지 검증한다.

```python
secret_token = "ghp_VERYSECRETTOKEN999"

with patch("gitshuttle.sync_.subprocess.run") as mock_run:
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "fatal: repository not found"
    mock_run.return_value = mock_result

    with pytest.raises(Exception) as exc_info:
        run_sync(
            source_url="https://github.com/org/repo",
            target_url="https://github.com/org/repo2",
            source_token=secret_token,
            work_dir=tmp_path,
        )

assert secret_token not in str(exc_info.value)
```

**효과:**  
보안 요구사항을 사람이 리뷰로만 확인하지 않고 테스트로 고정했다.  
토큰이 URL에 삽입되는 구조에서도 오류 메시지에는 마스킹된 값만 남도록 강제한다.

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

#### 사례 5 — replay CLI 옵션 전달 검증

`tests/test_cli.py`는 실제 patch 적용 없이 `run_import()`를 monkeypatch해서 `--mode replay`와 확인 콜백이 내부 API로 전달되는지 검증한다.

```python
def fake_run_import(..., import_mode="auto", confirm_duplicate_message=None):
    captured["import_mode"] = import_mode
    captured["has_confirm_callback"] = confirm_duplicate_message is not None
    return ImportResult(imported=1, skipped=0, total=1)

monkeypatch.setattr(import_module, "run_import", fake_run_import)

result = runner.invoke(app, [
    "import",
    "--file", str(patchset_path),
    "--repo", str(repo_dir),
    "--mode", "replay",
])

assert captured["import_mode"] == "replay"
assert captured["has_confirm_callback"] is True
```

**효과:**
느린 patch 생성·적용 없이 CLI 계약만 빠르게 확인한다.
실제 patchset 생성과 replay 적용은 `tests/test_patchset.py`가 임시 Git repo로 보완한다.

#### Mock 사용 시 주의점

Mock은 외부 의존성을 빠르고 안정적으로 격리하지만, 실제 Git 동작과 완전히 같지는 않다.  
그래서 GitShuttle은 mock 테스트만 두지 않고 `test_import.py`, `test_bundle.py`, `test_e2e.py`처럼 실제 임시 Git repo를 만들어 검증하는 테스트도 함께 둔다.

**정리:**  
Mock 테스트는 "명령 호출 방식", "오류 처리", "토큰 마스킹", "CLI 옵션 전달"을 빠르게 검증하고, 실제 Git repo 기반 테스트는 bundle 생성·검증·반입의 현실 동작을 보완한다.

---

*GitShuttle · Sprint 0~7 완료 + 기능 보강 · 168 tests collected · patchset/replay 및 patchset export 속도 개선 포함*
