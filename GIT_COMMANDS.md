# GitShuttle 내부 Git 명령어와 원리

이 문서는 GitShuttle이 내부적으로 어떤 Git 명령어를 사용하고, 왜 그렇게 설계되었는지를 정리한다.

핵심은 간단하다. GitShuttle은 patch 도구가 아니다. `git format-patch`, `git apply`, `git am`, `git cherry-pick`을 주 흐름으로 쓰지 않는다. 대신 `git bundle`로 이동 가능한 Git object 묶음을 만들고, import 시점에 필요하면 `git fast-export` stream을 재작성한 뒤 `git fast-import`로 대상 repo에 반영한다.

---

## 전체 구조

### Export

```text
source repo
  -> git log / rev-list / diff-tree 로 커밋 목록 조회
  -> git update-ref 로 임시 ref 생성
  -> git bundle create 로 .bundle 생성
  -> sha256 / manifest 생성
```

Git bundle은 Git object와 ref 정보를 담는 이동용 파일이다. USB, 망간 전송 시스템처럼 네트워크가 없는 환경에서도 Git 이력을 파일 하나로 옮길 수 있다.

선택 커밋만 bundle로 만들려면 Git이 도달 가능한 ref가 필요하다. 그래서 GitShuttle은 `refs/gitshuttle/tmp_*` 임시 ref를 만들고, bundle 생성 후 삭제한다.

### Import

import에는 두 경로가 있다.

```text
일반 import
  -> git bundle verify
  -> git bundle unbundle
  -> git merge 또는 checkout
```

```text
rewrite import
  -> git bundle verify
  -> 임시 bare repo 생성
  -> bundle refs fetch
  -> git fast-export
  -> author / timestamp / branch / parent rewrite
  -> git fast-import
  -> target branch checkout + reset --hard
```

작성자 변경, 시간 변경, target branch 지정, `--onto-ref` 같은 옵션을 쓰면 rewrite import 경로를 사용한다. 이 경로에서는 커밋 object가 새로 만들어지므로 SHA는 바뀔 수 있다.

---

## 이번 개발에서 중요했던 원리

### 1. bundle은 patch가 아니라 Git object 묶음

Patch는 파일 변경분을 텍스트 diff로 적용한다. 반면 bundle은 Git object 자체를 이동한다. 그래서 커밋 메시지, 작성자, 날짜, parent 관계, merge 이력 같은 Git 메타데이터를 더 자연스럽게 보존할 수 있다.

GitShuttle이 bundle을 선택한 이유는 다음과 같다.

- 망분리 환경에서 파일 하나로 옮기기 쉽다.
- Git history 단위의 이전이 가능하다.
- 선택 범위, 전체 브랜치, base 이후 delta를 모두 같은 개념으로 다룰 수 있다.
- import 시 rewrite가 필요하면 fast-export/fast-import stream으로 재작성할 수 있다.

### 2. fast-export stream은 텍스트처럼 보이지만 payload는 byte로 다뤄야 한다

`git fast-export` 출력에는 control line과 file payload가 섞여 있다.

```text
commit refs/heads/main
author A <a@example.com> 1 +0000
committer A <a@example.com> 1 +0000
data 12
commit msg
M 100644 :1 README.md
```

여기서 `data N` 다음의 N바이트는 커밋 메시지나 파일 내용이다. 파일 내용 안에 `from <sha>`나 `commit refs/...` 같은 문자열이 있어도 Git 명령어가 아니라 payload다.

그래서 GitShuttle은 다음 원칙을 지킨다.

- `fast-export` stdout은 binary로 캡처한다.
- Windows CRLF가 LF로 바뀌지 않게 한다.
- rewrite는 `data N` payload를 건너뛰고 control line만 대상으로 한다.

이 원칙을 어기면 `fast-import`가 파일 내용을 명령어로 오해해 `fatal: Unsupported command` 같은 오류가 날 수 있다.

### 3. author/time/branch 변경은 fast-export control line rewrite다

작성자 변경은 `author` / `committer` line을 바꾼다.

```text
author Old Name <old@example.com> 1710000000 +0900
```

브랜치 변경은 `commit refs/...` 또는 `reset refs/...` line을 target branch로 바꾼다.

```text
commit refs/heads/feat/work
```

시간 변경은 author/committer timestamp를 `now`, `original`, `from=<datetime>` 정책에 맞춰 조정한다.

### 4. `--base-branch` delta는 parent를 기준 ref로 치환한다

`--base-branch <base> --full-branch`는 `<base>..<feature>` 커밋만 선택한다. 단, 일반 range bundle은 대상 repo가 원본 base SHA를 갖고 있어야 검증된다.

GitShuttle은 이를 피하기 위해 export 단계에서 base metadata ref를 bundle 안에 함께 넣는다.

```text
refs/gitshuttle/base/...
```

import 단계에서는 metadata ref를 실제 import 대상에서 제외하고, fast-export의 excluded parent를 기준 ref tip으로 치환한다.

```text
원래 stream:
from <source-base-sha>

rewrite 후:
from <target-base-tip>
```

기준 ref는 다음 순서로 정한다.

```text
1. --onto-ref 가 있으면 그 ref/SHA/HEAD
2. 기존 target branch가 있으면 target branch tip
3. target branch가 없으면 현재 HEAD
```

### 5. full bundle도 `--onto-ref`로 graft할 수 있다

self-contained/full bundle은 root commit까지 포함할 수 있다. 이 경우 root commit에는 parent가 없어서, 기존 방식처럼 parent SHA를 치환할 대상이 없다.

이번 개발에서는 이 경우도 붙도록 root commit에 기준 parent를 주입했다.

```text
원래 stream:
commit refs/heads/feat/work
data 10
root msg
M 100644 :1 file.txt

rewrite 후:
commit refs/heads/feat/work
data 10
root msg
from <onto-ref-tip>
M 100644 :1 file.txt
```

이렇게 하면 기존 repo의 `develop`, `main`, `release/...`, `HEAD`, 특정 SHA 위에 full bundle 이력을 붙일 수 있다. GitHub PR에서도 완전히 분리된 unrelated history가 아니라 기준 브랜치 이후 변경처럼 비교할 수 있다.

### 6. fast-import 후에는 worktree를 직접 갱신해야 한다

`git fast-import`는 object DB와 ref를 갱신하지만, 일반 작업 폴더의 파일을 자동으로 바꾸지 않는다. 그래서 GitShuttle은 import 후 target branch로 이동하고 `reset --hard`를 실행한다.

```text
git checkout <target-branch>
git reset --hard <target-tip>
```

이 작업은 사용자 변경을 덮어쓸 수 있으므로, 먼저 `git status --porcelain`으로 작업 폴더가 깨끗한지 확인한다.

### 7. hidden original refs는 후속 증분 import를 돕는다

작성자나 날짜를 rewrite하면 커밋 SHA가 바뀐다. 그러면 다음에 일부 커밋만 담은 bundle을 가져올 때 원본 parent SHA를 대상 repo에서 찾지 못할 수 있다.

GitShuttle은 import 후 원본 bundle refs를 아래 namespace에 보관한다.

```text
refs/gitshuttle/original/<target-branch>/...
```

이 refs는 사용자 브랜치가 아니라 내부 기준점이다. 후속 증분 bundle import 때 임시 repo로 가져와 prerequisite 확인과 fast-export 범위 계산에 활용한다.

---

## 사용자가 기억할 핵심

- 내부 구현은 patch가 아니라 bundle + fast-export/fast-import다.
- `--target-branch`는 결과가 들어갈 브랜치 이름이다.
- `--onto-ref`는 import 이력을 어디 위에 붙일지 정하는 기준점이다.
- target branch가 없으면 현재 HEAD 또는 `--onto-ref` 위에 새로 만든다.
- target branch가 있는데 새 이력이 기존 tip을 포함하지 않으면 `--on-conflict force`가 필요할 수 있다.
- full bundle이 분리되어 PR이 안 되면 `--onto-ref <PR 대상 브랜치|HEAD|SHA> --on-conflict force`로 다시 import한다.
- import 후 worktree가 바뀌므로 대상 repo의 미커밋 변경은 먼저 정리해야 한다.

---

## 참조: 내부 Git 명령어 테이블

| 구분 | Git 명령어 | 사용 위치 | 목적 | 주의점 |
|------|------------|-----------|------|--------|
| 환경 확인 | `git --version` | 실행 전 검사 | Git 2.37 이상 확인 | 낮은 버전은 bundle/fast-export 동작 차이 가능 |
| 커밋 목록 | `git log <branch> --format=...` | export | TUI/CSV/recent/full-branch용 커밋 목록 조회 | null/record separator로 안전하게 파싱 |
| 부모 확인 | `git rev-list --parents -n 1 <commit>` | export, 테스트 | root commit 여부와 parent SHA 확인 | root commit은 parent가 없음 |
| 변경 파일 수 | `git diff-tree --root --no-commit-id -r --name-only <commit>` | export | 커밋별 변경 파일 수 계산 | root commit은 `--root` 필요 |
| 임시 ref 생성 | `git update-ref refs/gitshuttle/tmp_* <sha>` | export | bundle create가 참조할 임시 ref 생성 | bundle 생성 후 삭제해야 함 |
| 임시 ref 삭제 | `git update-ref -d <ref>` | export/import cleanup | 임시 refs 정리 | object는 남을 수 있음 |
| base ref 확인 | `git rev-parse --verify <ref>^{commit}` | export/import | branch/ref/SHA를 commit SHA로 해석 | `--onto-ref`가 잘못되면 실패 |
| bundle 생성 | `git bundle create <file> <refs...> ^<exclude...>` | export | 이동용 `.bundle` 생성 | range bundle은 prerequisite가 생김 |
| bundle 검증 | `git bundle verify <file>` | import | bundle 손상/prerequisite 확인 | rewrite import에서는 base metadata로 실패를 줄임 |
| bundle head 조회 | `git bundle list-heads <file>` | import | bundle 안의 tip ref 조회 | source branch 감지와 export 범위 계산에 사용 |
| 일반 반입 | `git bundle unbundle <file>` | non-rewrite import | bundle object를 target repo에 추가 | refs/gitshuttle 커스텀 ref 보존에는 한계가 있음 |
| 임시 repo 생성 | `git init --bare <tmp>` | rewrite import | bundle을 펼칠 임시 bare repo 준비 | worktree가 없는 object/ref 작업 공간 |
| bundle fetch | `git fetch <bundle> +refs/*:refs/*` | rewrite import | bundle의 모든 refs를 임시 repo로 가져오기 | metadata refs까지 가져온 뒤 export 대상에서 제외 |
| shadow refs fetch | `git fetch <repo> +refs/gitshuttle/original/*:refs/gitshuttle/original/*` | rewrite import | 이전 import의 원본 SHA refs를 임시 repo로 가져오기 | 후속 증분 import 기준점 |
| ref 목록 | `git for-each-ref --format=%(refname) refs/gitshuttle/original` | rewrite import | hidden original refs 존재 확인 | 사용자 브랜치가 아닌 내부 refs |
| fast-export | `git fast-export <args>` | rewrite import | Git 이력을 stream으로 추출 | stdout은 binary로 받아야 CRLF/data length 보존 |
| parent 표시 | `git fast-export --reference-excluded-parents ...` | delta import | 제외된 parent SHA를 stream에 남김 | 이후 기준 ref tip으로 치환 |
| fast-import | `git fast-import --quiet [--force]` | rewrite import | 재작성된 stream을 target repo에 커밋으로 반영 | `--force` 없으면 non-fast-forward ref 갱신 실패 가능 |
| HEAD 확인 | `git rev-parse --verify HEAD` | import | target repo의 현재 기준 commit 확인 | 빈 repo이면 실패 |
| branch tip 확인 | `git rev-parse refs/heads/<branch>` | import | target branch tip 확인 | 없는 branch면 새로 만들 수 있음 |
| bare 확인 | `git rev-parse --is-bare-repository` | import | worktree 갱신 필요 여부 판단 | bare repo는 checkout/reset 불가 |
| clean 확인 | `git status --porcelain` | import | 미커밋 변경 여부 확인 | 변경이 있으면 reset 전 중단 |
| checkout | `git checkout <branch>` | import 후 | target branch로 작업 폴더 이동 | 기존 작업 변경이 있으면 위험 |
| reset | `git reset --hard <tip>` | import 후 | worktree/index를 fast-import 결과와 동기화 | 사용자 변경 손실 방지를 위해 사전 clean 확인 |
| ancestor 확인 | `git merge-base --is-ancestor <tip> HEAD` | non-rewrite import | 이미 반영된 tip인지 확인 | exit code로 판단 |
| fast-forward merge | `git merge --ff-only <tip>` | non-rewrite import | 공통 이력일 때 빠르게 병합 | 불가능하면 다음 merge 전략 시도 |
| unrelated merge | `git merge --no-ff --allow-unrelated-histories -Xours ...` | non-rewrite import | 무관한 이력 병합 | 충돌 정책이 rewrite import와 다름 |
| merge abort | `git merge --abort` | non-rewrite import 실패 | 실패한 merge 정리 | abort도 실패할 수 있어 방어 처리 |
