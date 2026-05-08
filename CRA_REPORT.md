# CRA Report — GitShuttle

> **작성 가이드**  
> 이 문서는 GitShuttle 프로젝트의 기술적 성과를 분석합니다.  
> 1부: 프로젝트 개요 및 배경·기여 효과  
> 2부: Agents / TDD / Clean Code / Refactoring 네 가지 관점의 핵심 사례

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
```

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

---

*GitShuttle · Sprint 0~7 완료 · 106 tests PASSED · 0 failures*
