# GitShuttle 사용 예제

가장 많이 쓰는 흐름은 **기존 GitHub의 이력을 새 GitHub로 옮기면서 작성자와 시간을 바꾸는 것**입니다.
이 문서는 그 흐름을 먼저 설명하고, 나머지는 참고 예제로 정리합니다.

---

## 이름 규칙

아래 예제에서는 실제 계정/메일 대신 placeholder를 사용합니다.
명령을 실행할 때는 각 placeholder를 실제 값으로 바꿉니다.

| Placeholder | 의미 |
|-------------|------|
| `OLD_GITHUB_ID` | 이전 GitHub의 사용자 또는 조직 ID |
| `NEW_GITHUB_ID` | 이후 GitHub의 사용자 또는 조직 ID |
| `REPO_NAME` | 옮길 저장소 이름 |
| `OLD_AUTHOR_EMAIL` | 기존 커밋 author 이메일 |
| `NEW_AUTHOR_NAME` | 변경할 author/committer 이름 |
| `NEW_AUTHOR_EMAIL` | 변경할 author/committer 이메일 |
| `C:\repos\source-repo` | 이전 GitHub repo를 clone한 로컬 경로 |
| `C:\repos\target-repo` | 이후 GitHub repo를 clone한 로컬 경로 |
| `C:\transfer` | bundle, checksum, manifest를 저장할 폴더 |

---

## 대표 예제 — 이전 GitHub에서 이후 GitHub로 전체 이력 이전

### 1. 이전/이후 리포지토리 clone

이후 GitHub에는 빈 repository를 먼저 만들어 둡니다.

```powershell
git clone https://github.com/OLD_GITHUB_ID/REPO_NAME.git C:\repos\source-repo
git clone https://github.company.example/NEW_GITHUB_ID/REPO_NAME.git C:\repos\target-repo
```

사내 GitHub 주소는 회사 환경에 맞게 바꿉니다.

---

### 2. 기존 author 이메일 확인

```powershell
git -C C:\repos\source-repo log --all --format="%an <%ae>" | Sort-Object -Unique
```

출력된 이메일들을 `author_map.json`의 key로 사용합니다.
key는 `"Name <email>"` 형식이 아니라 **이메일 주소만** 써야 합니다.

---

### 3. 작성자 매핑 파일 작성

`C:\transfer\author_map.json` 파일을 만듭니다.

```json
{
  "OLD_AUTHOR_EMAIL": {
    "name": "NEW_AUTHOR_NAME",
    "email": "NEW_AUTHOR_EMAIL"
  },
  "ANOTHER_OLD_AUTHOR_EMAIL": {
    "name": "NEW_AUTHOR_NAME",
    "email": "NEW_AUTHOR_EMAIL"
  }
}
```

기존 작성자가 여러 명이어도 모두 같은 `NEW_AUTHOR_NAME <NEW_AUTHOR_EMAIL>`로 매핑할 수 있습니다.

---

### 4. 이전 repo 전체 이력 export

전체 브랜치를 TUI 선택 없이 한 번에 옮기려면 `--full-branch`를 사용합니다.

```powershell
python -m gitshuttle export `
  --repo C:\repos\source-repo `
  --branch main `
  --full-branch `
  --output C:\transfer
```

생성 파일:

```text
C:\transfer\shuttle_YYMMDD.bundle
C:\transfer\shuttle_YYMMDD.bundle.sha256
C:\transfer\shuttle_YYMMDD_manifest.txt
```

세 파일을 함께 옮깁니다.

---

### 5. 이후 repo에 import

바로 `main`에 넣기보다 migration 브랜치에 먼저 넣는 방식을 권장합니다.
이 대표 예제는 `--target-branch`와 `--timestamp original/from`을 사용하므로 rewrite import 경로입니다.
반대로 `gitshuttle import --file ...`만 실행하면 현재 브랜치로 merge될 수 있습니다.

```powershell
python -m gitshuttle import `
  --repo C:\repos\target-repo `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch migration/REPO_NAME-main `
  --timestamp original
```

날짜를 특정 기준일부터 다시 시작하게 하려면 `--timestamp from=`을 사용합니다.
예를 들어 `2026-06-10 09:00 KST` 기준으로 보이게 하려면 UTC 기준 `2026-06-10T00:00:00`을 입력합니다.

```powershell
python -m gitshuttle import `
  --repo C:\repos\target-repo `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch migration/REPO_NAME-main `
  --timestamp from=2026-06-10T00:00:00
```

`from=` 모드는 첫 커밋을 지정 시각으로 맞추고, 이후 커밋은 원본 커밋 간 상대 간격을 유지합니다.

---

### 6. 결과 확인

```powershell
git -C C:\repos\target-repo log migration/REPO_NAME-main `
  --format="%h %an <%ae> %cn <%ce> %ad %s" `
  --date=iso
```

확인할 것:

| 항목 | 확인 내용 |
|------|-----------|
| author | `NEW_AUTHOR_NAME <NEW_AUTHOR_EMAIL>`로 바뀌었는지 |
| committer | `NEW_AUTHOR_NAME <NEW_AUTHOR_EMAIL>`로 바뀌었는지 |
| branch | `migration/REPO_NAME-main` 브랜치에 생성됐는지 |
| files | 실제 파일들이 target repo 작업 폴더에 보이는지 |

GitHub 화면에서 "push한 사람"으로 보이는 계정은 커밋 author가 아니라 실제 push 인증 계정입니다.
그 표시까지 바꾸려면 `NEW_GITHUB_ID` 계정의 PAT 또는 SSH 인증으로 push해야 합니다.

---

### 7. 이후 GitHub로 push

검토용 브랜치로 먼저 올립니다.

```powershell
git -C C:\repos\target-repo push origin migration/REPO_NAME-main
```

이후 GitHub repo가 비어 있고 바로 `main`으로 올려도 되는 경우:

```powershell
git -C C:\repos\target-repo push origin migration/REPO_NAME-main:main
```

이미 `main`에 코드가 있다면 migration 브랜치를 push한 뒤 PR 또는 merge로 합칩니다.

```text
main 쪽:       X -> Y -------- M
                            /
import 쪽:        A -> B -> C
```

`Y`와 `A`가 직접 이어지는 것이 아니라, merge commit `M`이 `Y`와 `C`를 부모로 갖습니다.

```powershell
git -C C:\repos\target-repo switch main
git -C C:\repos\target-repo merge migration/REPO_NAME-main --allow-unrelated-histories
git -C C:\repos\target-repo push origin main
```

---

## 참고 1 — 이후 변경분만 추가 이전

최초 전체 이전을 완료한 뒤에는 새로 생긴 커밋만 선택해서 옮길 수 있습니다.

```powershell
python -m gitshuttle export `
  --repo C:\repos\source-repo `
  --branch main `
  --ui tui `
  --output C:\transfer

python -m gitshuttle import `
  --repo C:\repos\target-repo `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch migration/REPO_NAME-main `
  --timestamp original
```

최근 N개만 빠르게 옮기려면:

```powershell
python -m gitshuttle export `
  --repo C:\repos\source-repo `
  --branch main `
  --recent 2 `
  --bundle-scope full `
  --output C:\transfer
```

`--bundle-scope full`은 선택한 tip까지 필요한 이력을 함께 담아 부분 bundle prerequisite 실패를 줄입니다.

`main`에서 딴 feature 브랜치의 신규 커밋만 옮기려면 기준 브랜치를 명시합니다.

```powershell
python -m gitshuttle export `
  --repo C:\repos\source-repo `
  --branch feature/work `
  --base-branch main `
  --full-branch `
  --output C:\transfer

git -C C:\repos\target-repo switch -c migration/feature-work main

python -m gitshuttle import `
  --repo C:\repos\target-repo `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch migration/feature-work `
  --timestamp original
```

이 흐름에서는 `main..feature/work` 커밋을 선택합니다. bundle은 대상 repo 검증을 위해 기준점 metadata도 함께 담지만, import는 기준점 이전 이력을 반영하지 않고 이미 존재하는 `migration/feature-work` tip 위에 신규 커밋만 이어붙입니다.
`migration/feature-work` 브랜치를 미리 만들지 않았다면 import 시점의 현재 HEAD 위에 새 브랜치가 만들어집니다. 어떤 기준에 붙일지 명확히 하려면 import 전에 `git switch main` 또는 `git switch -c migration/feature-work main`을 먼저 실행하세요.
대상 repo가 원본 `main`의 기준 SHA를 갖고 있지 않아도 이 방식으로 import할 수 있습니다. 단, 예전 버전으로 만든 bundle은 기준점 metadata가 없으므로 같은 검증 오류가 나면 최신 버전으로 다시 export하세요.

이미 `migration/feature-work`가 분리된 이력으로 만들어져 GitHub에서 `main`으로 PR이 안 된다면, `main`을 기준으로 다시 graft합니다.

```powershell
git -C C:\repos\target-repo switch main

python -m gitshuttle import `
  --repo C:\repos\target-repo `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch migration/feature-work `
  --onto-ref main `
  --timestamp original `
  --on-conflict force
```

이 명령은 기존 `migration/feature-work` ref를 덮어쓰지만, 새 이력의 부모를 `main` tip으로 만들어 PR 비교가 가능하게 합니다.

---

## 참고 2 — CSV로 커밋 선택

TUI 대신 Excel/메모장으로 선택하려면 CSV 모드를 사용합니다.

```powershell
python -m gitshuttle export `
  --repo C:\repos\source-repo `
  --branch main `
  --ui csv `
  --output C:\transfer
```

생성된 `commits.csv`의 `include` 컬럼을 `Y` 또는 `N`으로 바꾼 뒤 안내에 따라 다시 실행합니다.

---

## 참고 3 — 빈 repo로 테스트 이전

실제 이후 GitHub에 넣기 전에 로컬 빈 repo에서 먼저 검증할 수 있습니다.

```powershell
git init C:\repos\target-test-repo

python -m gitshuttle import `
  --repo C:\repos\target-test-repo `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch migration/test `
  --timestamp original

git -C C:\repos\target-test-repo log migration/test --oneline
```

---

## 자주 하는 실수

| 실수 | 올바른 방법 |
|------|-------------|
| `author_map.json` key를 `"Name <email>"`로 작성 | key는 `"OLD_AUTHOR_EMAIL"`처럼 이메일만 작성 |
| 사내 GitHub URL을 `https:/...`처럼 슬래시 하나만 작성 | `https://github.company.example/...`처럼 슬래시 두 개 사용 |
| 기존 `main`에 바로 force import | `migration/...` 브랜치에 import 후 검토/merge |
| bundle만 옮기고 `.bundle.sha256`을 누락 | 가능하면 bundle, checksum, manifest 세 파일을 함께 이동 |
| 부분 bundle 검증 실패 | feature delta는 최신 버전으로 `--base-branch` + `--full-branch` 재export, 단순 최신 N개는 최초 전체 import 후 재시도하거나 `--bundle-scope full` 사용 |
