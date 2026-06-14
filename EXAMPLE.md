# GitShuttle 사용 예제

대표 시나리오를 단계별로 따라 할 수 있도록 정리했습니다.

---

## 예제 1 — 새 빈 레포에 최초 커밋 이전하기

**시나리오:** `gitshuttle` 레포의 가장 오래된 커밋 10개를 bundle로 만들어 완전히 비어 있는 새 레포 `gitshuttle_copyTest`에 이전합니다.

### 사전 준비

- Git 2.37 이상 설치
- Python 3.10 이상 + `pip install -r requirements.txt` 완료
- GitHub에 빈 레포 `gitshuttle_copyTest` 생성 (README 없이)

---

### Step 1 — 소스 레포에서 커밋 목록 확인

이전할 커밋이 어떤 것인지 먼저 확인합니다.

```
cd C:\projects\gitshuttle
git log --oneline | tail -10
```

**출력 예시 (오래된 순, 아래가 가장 오래됨):**
```
6b6b2b3 Add Direct Sync feature (Phase 2)
be1e3c3 Final update: REPORT.md session summary
5050df3 Untrack .mcp.json, add to .gitignore
bab5a4b Add .mcp.json initial template
06129f4 Add /github-mcp-setup skill and .gitignore
84ef04e Add PLAN.md: Phase 1 TDD development plan
48bce34 Add REPORT.md, update README/CLAUDE
dec3749 Add TDD harness with 4 SubAgents
adb9252 Add encoding config for Korean support
2891a21 Initial commit: PRD, README, CLAUDE.md
```

이 10개가 최초 10개(가장 오래된 순)입니다.

---

### Step 2 — 커밋 선택 후 Export (bundle 파일 생성)

아래 Python 스크립트로 최초 10개 커밋을 bundle로 만듭니다.  
출력 디렉터리는 원하는 경로(USB 드라이브 등)로 변경하세요.

```python
# export_initial_10.py
import sys
from pathlib import Path
sys.path.insert(0, '.')                      # gitshuttle 소스 루트에서 실행

from gitshuttle.git_ops import get_commits
from gitshuttle.export_ import run_export

repo    = Path('C:/projects/gitshuttle')     # 소스 레포 경로
out_dir = Path('C:/shuttle_transfer')        # 저장할 폴더 (USB 드라이브 등)
out_dir.mkdir(parents=True, exist_ok=True)

all_commits = get_commits(repo)              # 최신순 전체 커밋 목록
oldest_10   = all_commits[-10:]             # 마지막 10개 = 가장 오래된 10개

result = run_export(
    repo_path=repo,
    commits=oldest_10,
    output_dir=out_dir,
    branch='main',
    filename='gitshuttle_initial_10',        # 파일명 지정 (확장자 자동 추가)
)

print(f"bundle   : {result.bundle}")
print(f"sha256   : {result.sha256}")
print(f"manifest : {result.manifest}")
```

```
python export_initial_10.py
```

**출력 예시:**
```
bundle   : C:\shuttle_transfer\gitshuttle_initial_10.bundle
sha256   : C:\shuttle_transfer\gitshuttle_initial_10.bundle.sha256
manifest : C:\shuttle_transfer\gitshuttle_initial_10_manifest.txt
```

---

### Step 3 — 생성 파일 확인

`C:\shuttle_transfer\` 폴더에 파일 3개가 생성됩니다.

```
C:\shuttle_transfer\
├── gitshuttle_initial_10.bundle        ← 히스토리 패키지 (핵심)
├── gitshuttle_initial_10.bundle.sha256 ← 무결성 검증용 체크섬
└── gitshuttle_initial_10_manifest.txt  ← 커밋 목록 요약 (심사용)
```

manifest 내용을 미리 확인해 어떤 커밋이 포함됐는지 검토할 수 있습니다:

```
type C:\shuttle_transfer\gitshuttle_initial_10_manifest.txt
```

---

### Step 4 — 빈 타겟 레포 준비

대상 레포를 로컬에 새로 만듭니다. GitHub에서 clone하거나 로컬에서 `git init`합니다.

```
git init C:\projects\gitshuttle_copyTest
cd C:\projects\gitshuttle_copyTest
git config user.email "your@email.com"
git config user.name  "Your Name"
```

> GitHub에 미리 만들어 둔 경우: `git clone https://github.com/username/gitshuttle_copyTest.git`

---

### Step 5 — Import (bundle 반입)

bundle 파일이 있는 경로를 지정해 import합니다.  
타겟 레포 디렉터리에서 실행하세요.

```
cd C:\projects\gitshuttle_copyTest
python -m gitshuttle import --file C:\shuttle_transfer\gitshuttle_initial_10.bundle
```

**출력 예시:**
```
bundle   : C:\shuttle_transfer\gitshuttle_initial_10.bundle
target   : C:\projects\gitshuttle_copyTest
conflict : skip
반입을 시작합니다...

import 완료.
  imported : 10개
  skipped  :  0개
  total    : 10개
```

---

### Step 6 — 결과 확인

```
cd C:\projects\gitshuttle_copyTest
git log --oneline
```

**출력 예시:**
```
6b6b2b3 Add Direct Sync feature (Phase 2)
be1e3c3 Final update: REPORT.md session summary
5050df3 Untrack .mcp.json, add to .gitignore
bab5a4b Add .mcp.json initial template
06129f4 Add /github-mcp-setup skill and .gitignore
84ef04e Add PLAN.md: Phase 1 TDD development plan
48bce34 Add REPORT.md, update README/CLAUDE
dec3749 Add TDD harness with 4 SubAgents
adb9252 Add encoding config for Korean support
2891a21 Initial commit: PRD, README, CLAUDE.md
```

merge commit이 없는지 확인:

```
git log --merges --oneline
```

아무것도 출력되지 않으면 **merge commit 0개** — 원본 커밋만 깔끔하게 반영된 것입니다.

---

### Step 7 — GitHub에 push

```
git remote add origin https://github.com/username/gitshuttle_copyTest.git
git push -u origin main
```

---

## 예제 2 — 파일 저장 후 증분 업데이트 (11~20번째 커밋)

**시나리오:** 예제 1에서 이전한 레포에 다음 10개 커밋(#11~#20)을 추가로 이전합니다.  
bundle 파일을 `C:\shuttle_transfer\`에 저장해 두었다가 내부망에서 반입하는 흐름을 시뮬레이션합니다.

> 증분 bundle은 대상 repo에 직전 원본 부모 커밋 SHA가 있어야 검증됩니다.  
> 작성자/날짜 rewrite를 적용해 커밋 SHA가 바뀐 대상 repo에서는 최근 몇 개 커밋만 담은 증분 bundle이 `bundle 검증 실패`가 될 수 있습니다.
> 그 경우 필요한 전체 범위를 다시 export/import하세요.

### 사전 준비

- 예제 1이 완료된 상태 (`gitshuttle_copyTest`에 커밋 10개 존재)
- 소스 레포(`gitshuttle`)에 30개 이상 커밋 존재

---

### Step 1 — 11~20번째 커밋 확인

```
cd C:\projects\gitshuttle
git log --oneline | tail -20 | head -10
```

**출력 예시 (11번째 오래된 커밋부터 20번째까지):**
```
fca94dd Sprint 2: Export 핵심 + TUI 구현
d73c4e2 plan: Sprint 5 대용량 테스트 범위 축소
f62a158 docs: MANUAL.md 사용자 매뉴얼 A to Z 작성
0aadff3 Merge sprint/1-git-core: Git 핵심 레이어
d9c4ff3 Sprint 1: Git 핵심 레이어 구현
81127c7 Merge sprint/0-scaffold: 프로젝트 기반 구조
36cfe31 Sprint 0: 프로젝트 기반 구조 스캐폴딩
833e752 Final update: REPORT.md session close
971c872 Add mandatory doc update rule to CLAUDE.md
ba95f50 Update REPORT.md: Direct Sync feature log
```

---

### Step 2 — 11~20번째 커밋을 파일로 Export

아래 스크립트를 소스 레포 루트에서 실행합니다.

```python
# export_11to20.py
import sys
from pathlib import Path
sys.path.insert(0, '.')

from gitshuttle.git_ops import get_commits
from gitshuttle.export_ import run_export

repo    = Path('C:/projects/gitshuttle')
out_dir = Path('C:/shuttle_transfer')        # 이미 있는 폴더, 덮어쓰기 가능
out_dir.mkdir(parents=True, exist_ok=True)

all_commits = get_commits(repo)

# 전체 30개 중 11~20번째(오래된 순)
# get_commits()는 최신순 반환이므로: [-20:-10]
commits_11_20 = all_commits[-20:-10]

print(f"총 커밋: {len(all_commits)}개 / 선택: {len(commits_11_20)}개")
for i, c in enumerate(reversed(commits_11_20), start=11):
    print(f"  #{i:2d}  {c.short_hash}  {c.message}")

result = run_export(
    repo_path=repo,
    commits=commits_11_20,
    output_dir=out_dir,
    branch='main',
    filename='gitshuttle_11to20',
)

print(f"\nbundle   : {result.bundle}")
print(f"sha256   : {result.sha256}")
print(f"manifest : {result.manifest}")
print(f"크기     : {result.bundle.stat().st_size:,} bytes")
```

```
python export_11to20.py
```

**출력 예시:**
```
총 커밋: 30개 / 선택: 10개
  #11  ba95f50  Update REPORT.md: Direct Sync feature log
  #12  971c872  Add mandatory doc update rule to CLAUDE.md
  ...
  #20  fca94dd  Sprint 2: Export 핵심 + TUI 구현

bundle   : C:\shuttle_transfer\gitshuttle_11to20.bundle
sha256   : C:\shuttle_transfer\gitshuttle_11to20.bundle.sha256
manifest : C:\shuttle_transfer\gitshuttle_11to20_manifest.txt
크기     : 36,548 bytes
```

---

### Step 3 — 저장된 파일 확인

`C:\shuttle_transfer\` 폴더 상태:

```
C:\shuttle_transfer\
├── gitshuttle_initial_10.bundle         ← 예제 1에서 생성한 파일 (그대로 유지)
├── gitshuttle_initial_10.bundle.sha256
├── gitshuttle_initial_10_manifest.txt
├── gitshuttle_11to20.bundle             ← 이번에 새로 생성
├── gitshuttle_11to20.bundle.sha256
└── gitshuttle_11to20_manifest.txt
```

> 실제 망분리 환경에서는 이 3개 파일을 USB에 담아 내부망으로 이동합니다.

manifest 내용 미리 확인:

```
type C:\shuttle_transfer\gitshuttle_11to20_manifest.txt
```

---

### Step 4 — 타겟 레포 clone (내부망 시뮬레이션)

내부망 PC에 타겟 레포를 clone합니다.  
이미 로컬에 있다면 `git pull`로 최신 상태로 맞춥니다.

```
git clone https://github.com/username/gitshuttle_copyTest.git
cd gitshuttle_copyTest
git log --oneline
```

**현재 상태 확인 — 10개 커밋이 있어야 합니다:**
```
6b6b2b3 Add Direct Sync feature (Phase 2)
...
2891a21 Initial commit: PRD, README, CLAUDE.md
```

---

### Step 5 — Import (저장된 bundle 파일로 반입)

저장해 둔 파일을 지정해 import합니다.

```
cd C:\projects\gitshuttle_copyTest
python -m gitshuttle import --file C:\shuttle_transfer\gitshuttle_11to20.bundle
```

**출력 예시:**
```
bundle   : C:\shuttle_transfer\gitshuttle_11to20.bundle
target   : C:\projects\gitshuttle_copyTest
conflict : skip
반입을 시작합니다...

import 완료.
  imported : 10개
  skipped  :  0개
  total    : 10개
```

---

### Step 6 — 결과 확인

```
cd C:\projects\gitshuttle_copyTest
git log --oneline
```

**출력 예시 (누적 20개):**
```
fca94dd Sprint 2: Export 핵심 + TUI 구현       ← 20번째 (방금 추가)
d73c4e2 plan: Sprint 5 대용량 테스트 범위 축소
f62a158 docs: MANUAL.md 사용자 매뉴얼 A to Z 작성
0aadff3 Merge sprint/1-git-core: Git 핵심 레이어
d9c4ff3 Sprint 1: Git 핵심 레이어 구현
81127c7 Merge sprint/0-scaffold: 프로젝트 기반 구조
36cfe31 Sprint 0: 프로젝트 기반 구조 스캐폴딩
833e752 Final update: REPORT.md session close
971c872 Add mandatory doc update rule to CLAUDE.md
ba95f50 Update REPORT.md: Direct Sync feature log  ← 11번째
6b6b2b3 Add Direct Sync feature (Phase 2)           ← 10번째 (예제 1에서 반입)
...
2891a21 Initial commit: PRD, README, CLAUDE.md      ← 1번째
```

gitshuttle이 추가한 merge commit이 없는지 확인:

```
git log --merges --oneline
```

원본 히스토리에 있던 merge commit(`Merge sprint/0-scaffold`, `Merge sprint/1-git-core`)만 보이고,  
gitshuttle이 추가한 merge commit은 **0개**입니다.

---

### Step 7 — GitHub에 push

```
git push origin main
```

---

## 예제 3 — 다른 리포에서 Import Rewrite 적용 (작성자·브랜치·타임스탬프 재작성)

**시나리오:** `gitshuttle` 리포의 초기 10개 커밋을 `gitshuttle_copyTest`로 이전하면서,
작성자를 내부 계정으로 교체하고, 별도 브랜치로 격리하고, 반입 기준일을 타임스탬프로 지정합니다.

**조건:**
- 소스 작성자: `Tim <ltw070@naver.com>`
- 변경 후 작성자: `tw070-lim <tw070-lim@users.noreply.github.com>`
- 타겟 브랜치: `feat/gitshuttle_1st` (타겟의 main은 건드리지 않음)
- 타임스탬프 기준: `2026-05-09 10:23 AM KST` 부터, 이후 커밋은 원본 상대 간격 유지

---

### Step 1 — 타겟 리포 초기화

이미 내용이 있는 `gitshuttle_copyTest`를 빈 상태로 리셋합니다.

```bash
git clone https://github.com/ltw070/gitshuttle_copyTest /tmp/gs_copytest
cd /tmp/gs_copytest

# orphan 브랜치로 히스토리 완전 삭제 후 force push
git checkout --orphan fresh_init
git rm -rf .
git commit --allow-empty -m "chore: reset repository"
git push --force origin HEAD:main

# 원격 상태와 로컬 동기화 + 잔여 파일 제거
git fetch origin
git reset --hard origin/main
git clean -fdx
```

> `git clean -fdx`를 반드시 실행해야 untracked 파일(이전 클론에서 남은 gitshuttle/ 디렉터리 등)이 제거됩니다.

---

### Step 2 — 소스 리포에서 초기 10개 커밋 bundle 생성

소스 리포(`gitshuttle`)에서 가장 오래된 10번째 커밋을 기준으로 bundle을 만듭니다.

```bash
cd D:/cla/03_gitshuttle    # 소스 리포 경로

# 10번째 커밋 해시 확인 (오래된 순 10번째)
TENTH=$(git log --reverse --format="%H" | sed -n '10p')
echo "10th commit: $TENTH"

# 임시 브랜치 생성 → bundle → 정리
git checkout -b temp_export_10 $TENTH
git bundle create /tmp/first10.bundle temp_export_10
git checkout main
git branch -d temp_export_10
```

> 임시 브랜치를 만드는 이유: bundle에 named ref를 포함시켜야 `gitshuttle import`가 소스 브랜치명을 감지할 수 있습니다.

---

### Step 3 — 작성자 매핑 파일 생성

매핑 파일의 **키는 이메일 주소**만 사용합니다 (`"Name <email>"` 형식이 아님).
값은 `{"name": "...", "email": "..."}` dict 형식입니다.

```bash
cat > /tmp/author_map.json << 'EOF'
{
  "ltw070@naver.com": {"name": "tw070-lim", "email": "tw070-lim@users.noreply.github.com"}
}
EOF
```

> **주의:** `"Tim <ltw070@naver.com>"` 처럼 이름+이메일을 키로 쓰면 매핑이 동작하지 않습니다.

---

### Step 4 — Import (Rewrite 적용)

타겟 리포 디렉터리에서 실행합니다. `PYTHONPATH`로 gitshuttle 소스를 명시합니다.

```bash
cd /tmp/gs_copytest

PYTHONPATH=D:/cla/03_gitshuttle python -m gitshuttle import \
  --file /tmp/first10.bundle \
  --author-map /tmp/author_map.json \
  --target-branch "feat/gitshuttle_1st" \
  --timestamp "from=2026-05-09T01:23:00"
```

> **타임스탬프 시각 계산:** `--timestamp from=` 값은 UTC 기준입니다.
> 10:23 AM KST(UTC+9) = 01:23 UTC → `from=2026-05-09T01:23:00` 으로 입력합니다.

**출력 예시:**
```
bundle        : /tmp/first10.bundle
target        : /tmp/gs_copytest
conflict      : skip
target-branch : feat/gitshuttle_1st
author-map    : /tmp/author_map.json
timestamp     : from=2026-05-09T01:23:00
반입을 시작합니다...

import 완료.
  imported : 10개
  skipped  :  0개
  total    : 10개
```

> 미매핑 작성자가 있으면 `[경고] 매핑되지 않은 작성자:` 메시지가 stderr에 출력됩니다.
> 경고가 없으면 모든 작성자가 정상 치환된 것입니다.

---

### Step 5 — 결과 확인

```bash
cd /tmp/gs_copytest
git log feat/gitshuttle_1st --format="%H %an <%ae> %ad %s" \
  --date=format:"%Y-%m-%d %H:%M %Z"
```

**출력 예시:**
```
6b0c157 tw070-lim <tw070-lim@users.noreply.github.com> 2026-05-09 10:51 KST  Add Direct Sync feature (Phase 2)
c4f595 tw070-lim <tw070-lim@users.noreply.github.com> 2026-05-09 10:46 KST  Final update: REPORT.md session summary
...
da9e68 tw070-lim <tw070-lim@users.noreply.github.com> 2026-05-09 10:23 KST  Initial commit: PRD, README, CLAUDE.md
```

확인 포인트:
- 작성자: `tw070-lim <tw070-lim@users.noreply.github.com>` ← 치환됨
- 첫 커밋 시각: `10:23` ← 지정한 시각
- 타겟 `main` 브랜치: 변경 없음 (`feat/gitshuttle_1st`만 생성됨)

```bash
# main은 빈 상태 그대로 유지되어야 함
git log main --oneline
# → chore: reset repository (1개만)
```

---

### Step 6 — GitHub에 push

```bash
git push origin feat/gitshuttle_1st
```

**출력 예시:**
```
remote: Create a pull request for 'feat/gitshuttle_1st' on GitHub by visiting:
remote:   https://github.com/ltw070/gitshuttle_copyTest/pull/new/feat/gitshuttle_1st
To https://github.com/ltw070/gitshuttle_copyTest
 * [new branch]      feat/gitshuttle_1st -> feat/gitshuttle_1st
```

---

### 이 예제에서 배운 점

| 항목 | 주의사항 |
|------|----------|
| 브랜치명 | 콜론(`:`) 사용 불가 — 슬래시(`/`)로 대체: `feat/gitshuttle_1st` |
| author_map 키 | 이메일 주소만 (`"ltw070@naver.com"`), `"Name <email>"` 형식 아님 |
| 타임스탬프 | `from=` 값은 UTC 기준. 10:23 AM KST = `01:23 UTC` |
| git clean | 리셋 후 반드시 `git clean -fdx` 실행 (untracked 파일 제거) |
| PYTHONPATH | 타겟 리포와 gitshuttle 소스가 다른 경로일 때 `PYTHONPATH` 명시 필요 |

---

## 예제 4 — 일반 GitHub에서 사내 GitHub로 전체 이력 이전

**시나리오:** 외부 GitHub의 `ltw070/gitshuttle` 전체 이력을 사내 GitHub의 `tw070-lim/gitshuttle`로 옮깁니다.  
커밋 author/committer는 한 사용자(`ltw070 <ltw070@naver.com>`)로 통일하고, import 결과는 별도 브랜치에 올립니다.

> 사내 GitHub URL은 `https://github.samsungds.net/...`처럼 슬래시가 두 개 들어가야 합니다.

---

### Step 1 — 외부/사내 리포지토리 clone

```powershell
git clone https://github.com/ltw070/gitshuttle.git C:\repos\source-gitshuttle
git clone https://github.samsungds.net/tw070-lim/gitshuttle.git C:\repos\target-gitshuttle
```

사내 리포지토리는 GitHub에서 빈 repo로 먼저 만들어 둡니다.

---

### Step 2 — 원본 작성자 이메일 확인

```powershell
git -C C:\repos\source-gitshuttle log --all --format="%an <%ae>" | Sort-Object -Unique
```

출력된 모든 이메일을 다음 단계의 `author_map.json` 키로 넣습니다.

---

### Step 3 — 모든 작성자를 한 명으로 매핑

`C:\transfer\author_map.json` 파일을 만듭니다.

```json
{
  "old-user-1@example.com": {
    "name": "ltw070",
    "email": "ltw070@naver.com"
  },
  "old-user-2@example.com": {
    "name": "ltw070",
    "email": "ltw070@naver.com"
  }
}
```

키는 `"Name <email>"`이 아니라 이메일 주소만 사용합니다.

---

### Step 4 — 전체 이력을 선택 없이 export

`GITSHUTTLE_HEADLESS=1`을 켜면 TUI 선택 없이 조회된 커밋 전체가 선택됩니다.

```powershell
$env:GITSHUTTLE_HEADLESS = "1"

python -m gitshuttle export `
  --repo C:\repos\source-gitshuttle `
  --branch main `
  --ui tui `
  --output C:\transfer

Remove-Item Env:\GITSHUTTLE_HEADLESS
```

생성 파일:

```text
C:\transfer\shuttle_YYMMDD.bundle
C:\transfer\shuttle_YYMMDD.bundle.sha256
C:\transfer\shuttle_YYMMDD_manifest.txt
```

---

### Step 5 — 사내 리포지토리에 import

```powershell
python -m gitshuttle import `
  --repo C:\repos\target-gitshuttle `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch migration/gitshuttle-20260610 `
  --timestamp original
```

커밋 날짜를 새 기준일로 옮기려면 `--timestamp from=`을 사용합니다.

```powershell
# 2026-06-10 09:00 KST로 보이게 하려면 UTC 00:00 입력
python -m gitshuttle import `
  --repo C:\repos\target-gitshuttle `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch migration/gitshuttle-20260610 `
  --timestamp from=2026-06-10T00:00:00
```

> 현재 `from=` 모드는 첫 커밋을 지정 시각으로 맞추고 이후 커밋은 원본 상대 간격을 유지합니다.  
> 30분 고정 간격으로 모든 커밋을 재배치하는 옵션은 아직 없습니다.

---

### Step 6 — 결과 확인

```powershell
git -C C:\repos\target-gitshuttle log migration/gitshuttle-20260610 `
  --format="%h %an <%ae> %cn <%ce> %ad %s" `
  --date=iso
```

확인 포인트:

| 항목 | 확인 내용 |
|------|-----------|
| author | `ltw070 <ltw070@naver.com>`로 통일 |
| committer | `ltw070 <ltw070@naver.com>`로 통일 |
| branch | `migration/gitshuttle-20260610`에 생성 |
| 파일 내용 | 코드 안의 `author`, `commit refs/...` 문자열은 변경되지 않음 |

---

### Step 7 — 사내 GitHub로 push

검토용 브랜치로 먼저 올리는 방식:

```powershell
git -C C:\repos\target-gitshuttle push origin migration/gitshuttle-20260610
```

사내 리포지토리가 비어 있고 바로 `main`으로 올려도 되는 경우:

```powershell
git -C C:\repos\target-gitshuttle push origin migration/gitshuttle-20260610:main
```

GitHub 화면에서 "push한 사람"으로 보이는 계정은 커밋 author가 아니라 실제 push 인증 계정입니다.  
그 표시까지 바꾸려면 해당 계정의 PAT 또는 SSH 인증으로 push해야 합니다.

---

## 예제 1/2 비교

| 항목 | 예제 1 (최초 이전) | 예제 2 (증분 업데이트) |
|------|-------------------|----------------------|
| 대상 커밋 | 1~10번째 (가장 오래된 순) | 11~20번째 |
| 타겟 상태 | 완전히 빈 레포 | 이미 1~10개 커밋 존재 |
| bundle 전제 조건 | 없음 (루트 커밋 포함) | 10번째 커밋 필요 (자동 검증) |
| import 방식 | `git checkout -b main` | fast-forward merge |
| gitshuttle 추가 merge commit | 0개 | 0개 |
| bundle 크기 | 28,962 bytes | 36,548 bytes |

---

## 인덱스 계산 공식

`get_commits(repo)`는 **최신 → 오래된 순**으로 반환합니다.

| 원하는 범위 | Python 슬라이스 |
|------------|----------------|
| 가장 오래된 N개 | `all_commits[-N:]` |
| N~M번째 (오래된 순) | `all_commits[-(M):(-(N-1)) or None]` |
| 예) 11~20번째 | `all_commits[-20:-10]` |
| 예) 21~30번째 | `all_commits[-30:-20]` |
| 가장 최신 N개 | `all_commits[:N]` |

---

## 자주 하는 실수

**`--file` 경로에 공백이 있을 때**

```
# 잘못된 예
python -m gitshuttle import --file C:\My Folder\shuttle.bundle

# 올바른 예 (큰따옴표로 감쌈)
python -m gitshuttle import --file "C:\My Folder\shuttle.bundle"
```

**bundle 파일만 이동하고 .sha256을 빠뜨렸을 때**

```
[경고] 체크섬 파일을 찾을 수 없습니다: shuttle.bundle.sha256
SHA-256 검증을 생략합니다.
```

경고가 뜨지만 import는 계속됩니다. 보안이 중요한 환경에서는 반드시 3개 파일을 함께 이동하세요.

**이미 반입된 bundle을 다시 import할 때**

```
python -m gitshuttle import --file shuttle.bundle
# → imported: 0개, skipped: 0개, total: 0개
```

이미 모든 커밋이 존재하므로 아무것도 추가되지 않습니다. 정상 동작입니다.
