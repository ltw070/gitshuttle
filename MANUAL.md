# GitShuttle 사용자 매뉴얼

> 처음 사용하는 분도 따라 할 수 있도록 단계별로 설명합니다.

---

## 목차

1. [GitShuttle이란?](#1-gitshuttle이란)
2. [GitHub에서 받기](#2-github에서-받기)
3. [설치하기](#3-설치하기)
4. [설치 확인](#4-설치-확인)
5. [기본 워크플로우 한눈에 보기](#5-기본-워크플로우-한눈에-보기)
6. [export — 커밋 꾸러미 만들기](#6-export--커밋-꾸러미-만들기)
7. [import — 커밋 꾸러미 반입하기](#7-import--커밋-꾸러미-반입하기)
   - [7-1. 다른 리포에서 반입할 때 — Rewrite 기능](#7-1-다른-리포에서-반입할-때--rewrite-기능)
8. [config — 기본 설정 변경하기](#8-config--기본-설정-변경하기)
9. [커밋 선택 UI 4가지 방식](#9-커밋-선택-ui-4가지-방식)
10. [대용량 파일 분할 전송](#10-대용량-파일-분할-전송)
11. [sync — GitHub 직접 동기화 (Phase 2)](#11-sync--github-직접-동기화-phase-2)
12. [생성 파일 상세 설명](#12-생성-파일-상세-설명)
13. [충돌 처리 옵션 상세](#13-충돌-처리-옵션-상세)
14. [자주 묻는 질문 (FAQ)](#14-자주-묻는-질문-faq)
15. [오류 메시지 해설](#15-오류-메시지-해설)
16. [기존 GitHub에서 새 GitHub로 이전하기](#16-기존-github에서-새-github로-이전하기)

---

## 1. GitShuttle이란?

**GitShuttle**은 인터넷이 없는 망분리(Air-Gapped) 환경에서 Git 리포지토리의 커밋 히스토리를 안전하게 이전하는 도구입니다.

### 어떤 상황에서 쓰나요?

```
[외부망]  개발 PC에서 코드를 작성하고 커밋
    ↓
[USB]     GitShuttle로 만든 꾸러미 파일(bundle)을 USB에 담아 이동
    ↓
[내부망]  내부 Git 서버에 커밋 히스토리 그대로 반입
```

인터넷이 차단된 국방·금융·공공기관 등의 환경에서, 외부에서 작성한 코드를 내부망으로 가져올 때 사용합니다.

### 왜 단순 복사가 아닌가요?

소스 파일만 복사하면 커밋 메시지, 작성자, 변경 이력이 모두 사라집니다.  
GitShuttle은 Git의 모든 히스토리를 **100% 보존**합니다.

| 항목 | 단순 복사 | GitShuttle |
|------|-----------|------------|
| 커밋 메시지 | ❌ 사라짐 | ✅ 보존 |
| 커밋 작성자 | ❌ 사라짐 | ✅ 보존 |
| 브랜치 히스토리 | ❌ 사라짐 | ✅ 보존 |
| 파일 변조 감지 | ❌ 없음 | ✅ SHA-256 자동 검증 |

---

## 2. GitHub에서 받기

### 방법 A — 실행 파일(.exe) 다운로드 (Python 불필요, 권장)

> **현재 상태:** `gitshuttle.exe`는 아직 공개 릴리즈되지 않았습니다.
> 소스에서 직접 빌드하려면 아래 **직접 빌드** 방법을 참고하세요.

**릴리즈가 등록된 경우:**

1. 브라우저에서 아래 주소로 이동합니다:
   ```
   https://github.com/ltw070/gitshuttle/releases
   ```

2. 최신 릴리즈의 **Assets** 항목에서 `gitshuttle.exe`를 클릭하여 다운로드합니다.

3. 다운로드한 `gitshuttle.exe`를 원하는 폴더에 복사합니다. (예: `C:\tools\`)

**직접 빌드 (PyInstaller 설치 환경에서):**

```powershell
git clone https://github.com/ltw070/gitshuttle.git
cd gitshuttle
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File build.ps1
# → dist\gitshuttle.exe 생성
```

> **주의:** `.exe` 파일 한 개만 있으면 됩니다. Python 설치가 필요 없습니다.

---

### 방법 B — 소스 코드 다운로드 (Python 환경에서 실행)

Python이 이미 설치된 환경에서 직접 소스를 받아 실행하는 방식입니다.

**Git이 있는 경우 — 클론:**

```
git clone https://github.com/ltw070/gitshuttle.git
cd gitshuttle
```

**Git이 없는 경우 — ZIP 다운로드:**

1. `https://github.com/ltw070/gitshuttle` 접속
2. 초록색 **Code** 버튼 클릭 → **Download ZIP** 클릭
3. 다운로드된 ZIP 파일을 압축 해제합니다
4. 압축 해제된 폴더로 이동합니다

```
cd gitshuttle-main
```

---

## 3. 설치하기

### 방법 A — 실행 파일(.exe) 설치

별도 설치 과정이 없습니다. 다운로드한 `gitshuttle.exe`를 그냥 사용하면 됩니다.

**어디서나 실행하려면 PATH에 추가합니다:**

1. `C:\tools\` 폴더를 만들고 `gitshuttle.exe`를 복사합니다
2. Windows 검색에서 **"시스템 환경 변수 편집"** 검색 후 클릭
3. **"환경 변수"** 버튼 클릭
4. 사용자 변수의 **Path** 선택 → **편집** 클릭
5. **"새로 만들기"** 클릭 → `C:\tools` 입력 → **확인**

이후 터미널을 새로 열면 어디서든 `gitshuttle` 명령어를 사용할 수 있습니다.

---

### 방법 B — Python 환경 설치

소스 코드를 받은 폴더에서 아래 명령어를 실행합니다.

**1. Python 버전 확인 (3.10 이상 필요)**

```
python --version
```

출력 예시: `Python 3.11.5`

**2. 의존성 설치**

```
pip install -r requirements.txt
```

설치가 완료되면 아래와 같이 실행합니다:

```
python -m gitshuttle --help
```

---

## 4. 설치 확인

터미널(CMD, PowerShell, Windows Terminal)을 열고 아래 명령어를 입력합니다.

### .exe 방식

```
gitshuttle --help
```

### Python 방식

```
python -m gitshuttle --help
```

**정상 출력 예시:**

```
Usage: gitshuttle [OPTIONS] COMMAND [ARGS]...

  GitShuttle: 망분리 환경을 위한 Git 히스토리 동기화 도구.

Commands:
  export  선택한 커밋을 .bundle 파일로 추출합니다.
  import  shuttle 패키지를 현재 리포지토리에 반입합니다.
  config  대화형 마법사로 gitshuttle.toml 설정을 변경합니다.
  sync    두 GitHub 리포지토리 간 직접 동기화합니다.
```

이 화면이 나오면 설치가 완료된 것입니다.

> **이 매뉴얼의 이후 예시는 모두 `gitshuttle` 명령어로 표기합니다.**  
> Python 방식 사용자는 `gitshuttle` 대신 `python -m gitshuttle`을 입력하세요.

---

## 5. 기본 워크플로우 한눈에 보기

```
[외부망 PC]                                              [내부망 PC]
─────────────────────────────                    ─────────────────────────
1. 작업 디렉터리로 이동                              3. 작업 디렉터리로 이동
   cd C:\projects\my-repo                              cd C:\internal\my-repo

2. 커밋 꾸러미 생성                     USB →       4. 꾸러미 반입
   gitshuttle export                  이동           gitshuttle import
                                                        --file shuttle_260508.bundle
   생성된 파일 3개를 USB에 복사:
   • shuttle_260508.bundle            →→→→
   • shuttle_260508.sha256            →→→→
   • shuttle_260508_manifest.txt      →→→→
```

---

## 6. export — 커밋 꾸러미 만들기

export는 **외부망 PC**에서 실행합니다.

### 기본 실행

```
cd C:\projects\my-repo
gitshuttle export
```

커밋 목록이 TUI 화면에 나타납니다. 전송할 커밋을 선택한 뒤 Export하면 파일 3개가 생성됩니다.

### 전체 옵션

```
gitshuttle export [OPTIONS]
```

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--repo PATH` | 원본 Git 리포지토리 경로 지정 | `--repo C:\projects\my-repo` |
| `--branch TEXT` | 특정 브랜치의 커밋만 추출 | `--branch feature/login` |
| `--ui [tui\|csv\|html\|prompt]` | 커밋 선택 방식 | `--ui csv` |
| `--output TEXT` | 출력 경로 지정 | `--output C:\transfer` |
| `--format [bundle\|patchset]` | 패키지 형식. `patchset`은 replay/cherry-pick용 | `--format patchset` |
| `--patchset-compression [fast\|stored\|deflated]` | patchset 압축 방식. `stored`는 무압축이라 빠르지만 파일이 큼 | `--patchset-compression stored` |
| `--bundle-scope [range\|full]` | bundle 범위 방식. `full`은 선택 tip까지 전체 이력을 포함 | `--bundle-scope full` |
| `--full-branch` | 현재/지정 브랜치 tip 기준 전체 이력을 TUI 없이 bundle로 추출 | `--full-branch` |
| `--recent INTEGER` | UI 없이 최신 N개 커밋만 바로 선택 | `--recent 2` |

### 실행 예시

```
# 기본 (현재 브랜치, TUI 방식)
gitshuttle export

# main 브랜치만
gitshuttle export --branch main

# 현재 위치와 다른 폴더의 repo를 export
gitshuttle export --repo C:\projects\my-repo --branch main --output C:\transfer

# 현재/지정 브랜치 전체 이력을 TUI 없이 self-contained bundle로 export
gitshuttle export --repo C:\projects\my-repo --branch main --full-branch --output C:\transfer

# CSV 방식으로 Excel에서 선택
gitshuttle export --ui csv

# 출력 폴더를 직접 지정
gitshuttle export --output C:\transfer

# 기준점 없이 cherry-pick처럼 붙일 patchset 생성
gitshuttle export --format patchset --output C:\transfer

# 최신 2개 커밋만 TUI 없이 빠르게 patchset 생성
gitshuttle export --repo C:\projects\my-repo --branch main --format patchset --recent 2 --output C:\transfer

# patchset 생성 속도 우선: zip 무압축 저장
gitshuttle export --format patchset --patchset-compression stored --output C:\transfer

# 선택 tip 기준으로 부분 bundle prerequisite 없이 강제 연결 가능한 self-contained bundle 생성
gitshuttle export --format bundle --recent 2 --bundle-scope full --output C:\transfer
```

`--full-branch`는 브랜치 tip까지 도달 가능한 전체 이력을 포함합니다. merge된 서브브랜치 커밋은 포함되지만, 현재 브랜치에 merge되지 않은 독립 브랜치의 커밋은 포함되지 않습니다.

### 모든 커밋을 선택하고 TUI를 건너뛰기

TUI에서 하나씩 선택하지 않고 현재 브랜치의 모든 커밋을 export하려면 headless 모드를 사용합니다.

```powershell
$env:GITSHUTTLE_HEADLESS = "1"
gitshuttle export --repo C:\projects\my-repo --branch main --ui tui --output C:\transfer
Remove-Item Env:\GITSHUTTLE_HEADLESS
```

`GITSHUTTLE_HEADLESS=1`은 테스트·자동화용 우회 모드입니다. 설정되어 있는 동안 TUI 선택 없이 전체 커밋이 선택됩니다.

일부 커밋만 빠르게 선택하려면 headless보다 `--recent N`이 더 적합합니다. 이 옵션은 커밋 목록 조회 단계부터 최신 N개로 제한하므로, 큰 repo에서 TUI나 전체 로그 스캔 비용을 줄입니다.

### 실행 결과

export가 완료되면 현재 디렉터리에 파일 3개가 생성됩니다:

```
shuttle_260508.bundle        ← 이것이 핵심 파일
shuttle_260508.sha256        ← 무결성 검증용
shuttle_260508_manifest.txt  ← 커밋 목록 요약
```

**이 3개 파일을 모두 USB에 복사하여 내부망으로 전달하세요.**

---

## 7. import — 커밋 꾸러미 반입하기

import는 **내부망 PC**에서 실행합니다.

### 기본 실행

```
cd C:\internal\my-repo
gitshuttle import --file D:\USB\shuttle_260508.bundle
```

`--file` 뒤에 bundle 파일의 전체 경로를 입력합니다.

### 전체 옵션

```
gitshuttle import --file FILE [OPTIONS]
```

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--file TEXT` | bundle 또는 patchset 파일 경로 **(필수)** | — |
| `--repo PATH` | 대상 Git 리포지토리 경로 | 현재 디렉터리 |
| `--on-conflict [skip\|force\|abort]` | 충돌 처리 방식 | `skip` |
| `--author-map FILE` | 작성자 매핑 JSON 파일 경로 | 없음 (원본 유지) |
| `--target-branch TEXT` | import 커밋을 담을 브랜치명 | `imported/<소스브랜치>` |
| `--timestamp TEXT` | 커밋 타임스탬프 모드 | `now` |
| `--mode [auto\|bundle\|replay]` | import 방식. `.patchset`은 `auto`에서 replay로 처리 | `auto` |

### 실행 예시

```
# USB에서 반입 (기본: 중복 커밋은 건너뜀)
gitshuttle import --file D:\USB\shuttle_260508.bundle

# 현재 폴더에 있는 bundle 파일
gitshuttle import --file shuttle_260508.bundle

# 현재 위치와 다른 폴더의 repo에 반입
gitshuttle import --file D:\USB\shuttle_260508.bundle --repo C:\internal\my-repo

# 충돌 시 강제 덮어쓰기
gitshuttle import --file shuttle_260508.bundle --on-conflict force

# 중복 커밋 발견 즉시 전체 중단
gitshuttle import --file shuttle_260508.bundle --on-conflict abort

# patchset을 대상 브랜치 위에 cherry-pick처럼 재생
gitshuttle import --file shuttle_260508.patchset --mode replay --target-branch main
```

### 실행 흐름

import를 실행하면 자동으로 아래 과정이 진행됩니다:

```
1. SHA-256 체크섬 검증  →  파일이 전송 중 손상/변조되지 않았는지 확인
2. bundle 무결성 검사   →  Git bundle 형식이 올바른지 확인
3. 중복 커밋 확인       →  이미 반입된 커밋은 건너뜀 (--on-conflict 옵션 적용)
4. 히스토리 반영        →  새로운 커밋을 현재 리포지토리에 병합
5. 결과 출력            →  반입된 커밋 수, 건너뛴 커밋 수 표시
```

### 체크섬 불일치 오류

USB 이동 중 파일이 손상된 경우:

```
[오류] SHA-256 체크섬 불일치!
  기대값 (expected): a3f8c2d1e9b4...
  실제값 (actual):   7f2e91c4b8a3...

파일이 손상되었을 수 있습니다.
재export 방법: 소스 측에서 'gitshuttle export' 를 다시 실행하세요.
```

이 경우 외부망 PC에서 bundle 파일을 다시 생성하여 재전달해야 합니다.

---

## 7-1. 다른 리포에서 반입할 때 — Rewrite 기능

소스와 타겟이 **서로 다른 조직/리포지토리**인 경우, 작성자 정보·브랜치·타임스탬프를 타겟에 맞게 조정할 수 있습니다.

### 브랜치 격리 (Branch Isolation)

> 소스의 `main`/`master`를 타겟의 기존 기본 브랜치에 **직접 병합하지 않습니다.**
> 타겟에 별도 브랜치를 새로 만들어 커밋을 안전하게 격리합니다.

```
# 브랜치명 미지정 → 타겟에 'imported/main' 브랜치 자동 생성
gitshuttle import --file shuttle_260508.bundle

# 브랜치명 직접 지정
gitshuttle import --file shuttle_260508.bundle --target-branch ext-main
```

반입 후 타겟에서 직접 검토·머지 여부를 결정합니다:

```
git log imported/main --oneline    # 반입된 커밋 확인
git merge imported/main            # 검토 완료 후 병합
```

대상 repo의 `main`에 이미 코드가 있다면, 바로 `main`에 import하지 말고 별도 브랜치로 먼저 가져오는 방식을 권장합니다.

```powershell
gitshuttle import `
  --repo C:\repos\target `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --target-branch migration/source-main

git -C C:\repos\target switch main
git -C C:\repos\target merge migration/source-main --allow-unrelated-histories
```

이 방식에서는 기존 `main` 커밋이 브랜치 이력에 남고, bundle로 가져온 이력이 `migration/source-main`에 따로 들어갑니다. 병합 시 같은 파일이 양쪽에서 다르게 수정되어 있으면 Git merge conflict가 발생하며, 그때 최종 파일 내용을 직접 선택하면 됩니다.

`--target-branch main --on-conflict force`처럼 기본 브랜치를 직접 대상으로 지정하면 `main` ref가 import 결과로 이동할 수 있습니다. 기존 커밋 object가 즉시 삭제되는 것은 아니지만 `git log main`에서는 보이지 않을 수 있으므로, 기존 코드를 보존하면서 합치려면 별도 브랜치 import 후 merge 흐름을 사용하세요.

rewrite import가 완료되면 GitShuttle은 대상 브랜치로 checkout한 뒤 `reset --hard <브랜치 tip>`을 실행해 작업 폴더의 실제 파일도 import 결과와 맞춥니다.  
따라서 import 전 대상 repo에 커밋되지 않은 변경 사항이 있으면 먼저 commit/stash 하거나 정리해야 합니다.

---

### 작성자 매핑 (Author Mapping)

소스 repo의 커밋 작성자를 타겟 조직의 내부 계정으로 대체합니다.

**1. 매핑 파일 작성 (`author_map.json`):**

```json
{
  "jane@external.com": {
    "name": "홍길동",
    "email": "hong@internal.com"
  },
  "bob@external.com": {
    "name": "이철수",
    "email": "lee@internal.com"
  }
}
```

**2. import 실행:**

```
gitshuttle import --file shuttle_260508.bundle --author-map author_map.json
```

- 매핑 테이블에 없는 작성자는 원본 그대로 유지되며 경고 메시지가 출력됩니다.
- 매핑 키는 `"Name <email>"` 형식이 아니라 **이메일 주소만** 써야 합니다.
- `gitshuttle.toml`에는 매핑 파일 경로를 기본값으로 저장할 수 있습니다:

```toml
[import]
author_map = "C:\\transfer\\author_map.json"
```

---

### 커밋 타임스탬프 (Timestamp)

반입 시 커밋에 어떤 시각을 기록할지 선택합니다.

| 모드 | 설명 | 사용 예시 |
|------|------|-----------|
| `now` (기본값) | 모든 커밋 date = import 실행 시각 | 반입 이력 추적 |
| `original` | 소스 원본 날짜·시각 그대로 보존 | 개발 흐름 보존 |
| `from=<datetime>` | 최초 커밋을 지정 시각으로, 이후 커밋은 원본 상대 간격 유지 | 반입 심사 기준일 지정 |

```
# 기본 (반영 시각)
gitshuttle import --file shuttle_260508.bundle

# 소스 원본 시각 보존
gitshuttle import --file shuttle_260508.bundle --timestamp original

# 2024년 1월 1일 오전 9시부터 타임스탬프 시작
gitshuttle import --file shuttle_260508.bundle --timestamp from=2024-01-01T09:00:00
```

`from=` 값은 내부적으로 UTC 기준으로 해석됩니다. KST 오전 9시로 보이게 하려면 UTC로 9시간 빼서 입력합니다.

```powershell
# 2026-06-10 09:00 KST 기준으로 보이게 하려면
gitshuttle import --file shuttle.bundle --timestamp from=2026-06-10T00:00:00
```

`from=` 모드 동작 예시:

```
소스 커밋 원본:           2024-03-01  →  2024-03-05  →  2024-03-10
from=2024-01-01T09:00:00 적용:
  → 2024-01-01T09:00:00  →  2024-01-05T09:00:00  →  2024-01-10T09:00:00
     (최초 커밋 = 지정 시각)    (+4일 간격 유지)        (+5일 간격 유지)
```

`gitshuttle.toml`에 기본값으로 저장:

```toml
[import]
timestamp = "now"   # now | original | from=2024-01-01T09:00:00
author_map = "C:\\transfer\\author_map.json"
```

---

### 전체 결합 예시

```
gitshuttle import \
  --file shuttle_260508.bundle \
  --author-map author_map.json \
  --target-branch ext-main \
  --timestamp from=2024-05-22T09:00:00
```

---

### Replay / Cherry-Pick 방식

기준점 hidden ref 없이 작업자가 책임지고 변경분만 이어 붙이고 싶다면 `patchset` + `replay` 방식을 사용합니다.

```
gitshuttle export --repo C:\projects\source --branch main --format patchset --recent 2 --output C:\transfer

gitshuttle import ^
  --repo C:\projects\target ^
  --file C:\transfer\shuttle_YYMMDD.patchset ^
  --mode replay ^
  --target-branch main ^
  --author-map C:\transfer\author_map.json ^
  --timestamp original
```

replay는 원본 커밋 객체를 옮기는 것이 아니라 각 커밋의 diff를 대상 브랜치 현재 HEAD 위에 새 커밋으로 적용합니다.
따라서 기준점이 없어도 동작할 수 있지만, 커밋 SHA와 merge 구조는 원본과 달라질 수 있고 충돌이 나면 사용자가 직접 정리해야 합니다.

원본 첫 커밋부터 포함된 patchset을 아직 존재하지 않는 `--target-branch`로 replay하면 GitShuttle은 빈 orphan branch에서 시작합니다.
이 경우 대상 repo에 기존 README/license가 있어도 새 target branch에는 섞이지 않으며, 같은 파일을 여러 커밋에서 반복 수정한 전체 순차 replay도 중간 커밋을 빠뜨리지 않으면 적용됩니다.
반대로 이미 존재하는 대상 브랜치에 replay하면 그 브랜치의 현재 파일 상태가 patch의 기준 상태와 맞아야 합니다.
비어 있지 않은 브랜치에 원본 변경 파일을 강제로 덮어쓰려면 `--on-conflict force`를 사용합니다.
이 모드는 최신 patchset에 포함된 변경 파일 스냅샷을 사용해 해당 커밋의 변경 파일만 source-wins 방식으로 적용합니다.
기존 patchset에 스냅샷 metadata가 없으면 최신 GitShuttle로 다시 export해야 합니다.
patchset export는 선택 커밋을 Git topo order로 정렬해 서브브랜치 merge 이력이 날짜순으로 뒤섞여 replay되는 문제를 줄입니다.
서로 다른 브랜치에서 같은 파일을 바꾼 merge 충돌형 이력은 `--on-conflict force`를 사용해 merge commit의 최종 파일 상태를 반영하세요.

대상 브랜치의 마지막 커밋 메시지와 새로 붙일 첫 replay 커밋 메시지가 같으면 GitShuttle이 한 번만 경고하고 계속 진행 여부를 묻습니다.
메시지가 다르면 추가 확인 없이 replay를 진행합니다.

이미 같은 변경분이 대상 브랜치에 적용되어 있으면 해당 patch는 자동으로 건너뜁니다.
하지만 같은 경로의 파일이 이미 있고 내용이 다르면 `patch failed`, `patch does not apply`, `already exists in index` 계열 오류가 날 수 있습니다.
이 경우 오류 메시지에 실패한 replay 순번, 원본 커밋 hash, 제목, `git apply` 상세 출력이 함께 표시됩니다.
이미 반영된 커밋은 선택하지 말고 그 이후 커밋만 다시 patchset으로 만들거나, 대상 브랜치에서 충돌 파일을 직접 정리한 뒤 다시 실행하세요. 원본 변경 파일을 우선하려면 `--on-conflict force`로 재실행할 수 있습니다.

patchset export는 metadata를 커밋별로 반복 조회하지 않고 batch로 읽고, parent 정보도 patch 생성에 재사용합니다. 압축은 기본 `fast`이며, CPU 시간이 더 중요하면 `--patchset-compression stored`로 무압축 저장을 선택할 수 있습니다. 연속 선형 first-parent 범위는 `git format-patch --stdout` 기반으로 빠르게 생성하고, merge나 비연속 선택은 기존 커밋별 diff 방식으로 자동 fallback합니다.

---

## 8. config — 기본 설정 변경하기

매번 `--ui csv` 처럼 옵션을 입력하는 것이 번거롭다면, config 마법사로 기본값을 저장할 수 있습니다.

```
gitshuttle config
```

**실행 화면:**

```
GitShuttle 설정 마법사
======================

커밋 선택 UI 기본값을 선택하세요:
  [1] tui    — 터미널 인터랙티브 (현재: tui)
  [2] csv    — Excel/메모장 편집
  [3] html   — 브라우저에서 선택
  [4] prompt — 방향키 멀티셀렉트

선택 (1~4, 그냥 Enter는 현재값 유지): 2

저장 완료: gitshuttle.toml
```

이후 `gitshuttle export` 실행 시 자동으로 CSV 방식이 사용됩니다.

### 설정 파일 직접 편집

`gitshuttle.toml` 파일을 메모장으로 열어 직접 수정할 수도 있습니다.

```toml
[export]
ui = "csv"   # tui | csv | html | prompt
```

### 설정 파일 우선순위

```
--ui 옵션 (가장 높음)
    ↓
현재 디렉터리의 gitshuttle.toml
    ↓
홈 디렉터리(C:\Users\사용자명\)의 gitshuttle.toml
    ↓
기본값: tui (가장 낮음)
```

---

## 9. 커밋 선택 UI 4가지 방식

### 방식 1: TUI (기본값) — 터미널 인터랙티브

```
gitshuttle export
gitshuttle export --ui tui
```

터미널에서 키보드로 커밋을 선택하는 방식입니다.

```
┌──────────────────────────────────────────────────────────────┐
│ GitShuttle Export                          [Q] 취소  [E] Export │
├───┬────────┬──────────────┬───────────┬────────────────────── ┤
│ □ │ Hash   │ 날짜          │ 작성자    │ 커밋 메시지           │
├───┼────────┼──────────────┼───────────┼───────────────────────┤
│ □ │ a3f8c2 │ 2026-05-08   │ Alice     │ feat: 결제 모듈 추가  │
│ □ │ b9e4f7 │ 2026-05-07   │ Bob       │ fix: 로그인 버그 수정 │
│ ✓ │ c2d1e9 │ 2026-05-01   │ Alice     │ [imported] 초기 설정  │
└───┴────────┴──────────────┴───────────┴───────────────────────┘
```

| 키보드 | 동작 |
|--------|------|
| `↑` `↓` | 커서 이동 |
| `Space` | 현재 줄 선택/해제 |
| `Shift` + `↓/↑` | 범위 선택 |
| `A` | 전체 선택 / 전체 해제 |
| `E` | 선택 완료 후 Export 실행 |
| `Q` | 취소 |

`[imported]` 표시가 있는 커밋은 이미 내부망에 반입된 것입니다.

---

### 방식 2: CSV — Excel/메모장에서 선택

```
gitshuttle export --ui csv
```

1. 명령어를 실행하면 `commits.csv` 파일이 생성됩니다.

2. Excel 또는 메모장으로 파일을 열어 `include` 컬럼을 편집합니다:
   - `Y` = 전송할 커밋
   - `N` = 건너뛸 커밋

   ```csv
   include,hash,date,author,message,files_changed
   Y,a3f8c2,2026-05-08,Alice,feat: 결제 모듈 추가,5
   Y,b9e4f7,2026-05-07,Bob,fix: 로그인 버그 수정,2
   N,c2d1e9,2026-05-01,Alice,[imported] 초기 설정,8
   ```

3. 파일을 저장합니다.

4. 터미널로 돌아와 `Enter`를 누르면 export가 진행됩니다.

> Windows Terminal이 불편한 환경에서 특히 유용합니다.

---

### 방식 3: HTML — 브라우저에서 선택

```
gitshuttle export --ui html
```

1. 명령어를 실행하면 `commits_260508.html` 파일이 생성됩니다.

2. 해당 HTML 파일을 **브라우저(Chrome, Edge 등)로 드래그**하여 열거나 더블클릭합니다.

3. 브라우저 화면에서 체크박스로 전송할 커밋을 선택합니다.

4. **"Export"** 버튼을 클릭하면 `selection.json` 파일이 자동 다운로드됩니다.

5. `selection.json`을 커밋 작업 디렉터리에 놓으면 자동으로 export가 진행됩니다.

> 인터넷 연결이 **전혀 필요 없습니다.** HTML 파일 하나에 모든 기능이 내장되어 있습니다.

---

### 방식 4: Prompt — 터미널 방향키 멀티셀렉트

```
gitshuttle export --ui prompt
```

터미널에서 방향키와 `Space`로 선택하는 간단한 방식입니다.

```
? 전송할 커밋을 선택하세요 (Space: 선택/해제, Enter: 확인)
 ❯ ◉ a3f8c2 | 2026-05-08 | Alice  | feat: 결제 모듈 추가
   ○ b9e4f7 | 2026-05-07 | Bob    | fix: 로그인 버그 수정
   ○ c2d1e9 | 2026-05-01 | Alice  | [imported] 초기 설정
```

| 키보드 | 동작 |
|--------|------|
| `↑` `↓` | 커서 이동 |
| `Space` | 선택/해제 |
| `Enter` | 선택 완료 |

---

## 10. 대용량 파일 분할 전송

USB 용량 제한으로 bundle 파일 하나가 너무 클 때 사용합니다.

### 분할하기

```python
from gitshuttle.bundle import split_bundle

# 50MB 단위로 분할
parts = split_bundle("shuttle_260508.bundle", chunk_bytes=50 * 1024 * 1024)
```

분할 파일이 생성됩니다:
```
shuttle_260508.bundle.part000
shuttle_260508.bundle.part001
shuttle_260508.bundle.part002
...
```

### 재조립하기 (내부망에서)

```python
from gitshuttle.bundle import merge_bundles

merge_bundles(
    ["shuttle_260508.bundle.part000",
     "shuttle_260508.bundle.part001",
     "shuttle_260508.bundle.part002"],
    output="shuttle_260508_merged.bundle"
)
```

재조립이 완료되면 일반 import와 동일하게 진행합니다:

```
gitshuttle import --file shuttle_260508_merged.bundle
```

> **주의:** 분할된 파트 파일은 모두 이동해야 합니다. 일부 누락 시 재조립 불가합니다.

---

## 11. sync — GitHub 직접 동기화 (Phase 2)

> **네트워크가 연결된 환경에서만 사용합니다.**  
> 두 GitHub 리포지토리 사이에서 USB 없이 직접 커밋을 동기화합니다.

### 사전 준비

**1단계: 설정 파일 작성**

작업 디렉터리에 `gitshuttle.toml` 파일을 만들거나 `gitshuttle config`로 생성합니다.

```toml
[sync.source]
url  = "https://github.com/회사외부/repo"
auth = "token"

[sync.target]
url  = "https://github.com/회사내부/repo"
auth = "token"
```

**2단계: 토큰 환경변수 설정**

GitHub Personal Access Token을 환경변수로 전달합니다.  
(**절대 `gitshuttle.toml` 파일에 직접 토큰을 쓰지 마세요.**)

```
set GS_SOURCE_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
set GS_TARGET_TOKEN=ghp_yyyyyyyyyyyyyyyyyyyy
```

### 실행

> **현재 `gitshuttle sync` CLI는 Phase 2 준비 중입니다.**  
> 지금은 Python API로 직접 사용할 수 있습니다.

```python
import os
from gitshuttle.sync_ import run_sync

result = run_sync(
    source_url="https://github.com/org1/repo",
    target_url="https://github.com/org2/repo",
    source_token=os.environ["GS_SOURCE_TOKEN"],
    target_token=os.environ["GS_TARGET_TOKEN"],
)
print(f"동기화 완료: {result.synced}개 커밋")
```

### SSH 방식

토큰 대신 SSH 키를 사용하는 경우:

```toml
[sync.source]
url     = "git@github.com:org1/repo.git"
auth    = "ssh"
ssh_key = "C:\\Users\\사용자명\\.ssh\\id_rsa_source"

[sync.target]
url     = "git@github.com:org2/repo.git"
auth    = "ssh"
ssh_key = "C:\\Users\\사용자명\\.ssh\\id_rsa_target"
```

SSH 키 파일 경로의 백슬래시(`\`)는 두 번(`\\`) 씁니다.

---

## 12. 생성 파일 상세 설명

export 실행 시 아래 3개 파일이 생성됩니다.

### shuttle_YYMMDD.bundle

Git bundle 형식의 핵심 파일입니다. 선택한 커밋의 히스토리가 모두 담겨 있습니다.

- `YYMMDD`는 실행 날짜입니다. (예: 260508 = 2026년 5월 8일)
- `gitshuttle import --file` 명령어에 이 파일을 지정합니다.

### shuttle_YYMMDD.sha256

bundle 파일의 SHA-256 체크섬(해시값)이 저장된 텍스트 파일입니다.

```
a3f8c2d1e9b4f7a2c5d8e1f4b7c0d3e6f9a2b5c8  shuttle_260508.bundle
```

import 시 자동으로 체크섬이 검증됩니다. 파일이 손상/변조된 경우 즉시 오류를 알려줍니다.

### shuttle_YYMMDD_manifest.txt

포함된 커밋 목록을 사람이 읽기 쉬운 형식으로 요약한 파일입니다.

```
GitShuttle Manifest
생성일시: 2026-05-08 14:30:00
브랜치: main
커밋 수: 3

a3f8c2d1  2026-05-08  Alice  feat: 결제 모듈 추가      (5 files)
b9e4f7a2  2026-05-07  Bob    fix: 로그인 버그 수정      (2 files)
c2d1e9f3  2026-05-01  Alice  docs: README 갱신          (1 file)
```

반출입 심사 시 이 파일로 어떤 커밋이 포함되어 있는지 확인할 수 있습니다.

---

**3개 파일은 항상 함께 이동하세요.**  
`.sha256` 없이 import하면 체크섬 검증이 생략되어 파일 손상을 감지할 수 없습니다.

---

## 13. 충돌 처리 옵션 상세

"충돌"이란 import하려는 커밋이 대상 리포지토리에 이미 존재하는 상황을 말합니다.

| 옵션 | 동작 | 권장 상황 |
|------|------|-----------|
| `skip` (기본값) | 이미 있는 커밋은 건너뛰고 나머지를 계속 반입 | 증분 업데이트, 재전달 등 일반 상황 |
| `force` | 이미 존재해도 오류 없이 계속 진행. rewrite import에서는 기존 대상 브랜치 ref도 덮어씀 | 히스토리를 확실히 덮어써야 할 때 |
| `abort` | 이미 있는 커밋이 하나라도 발견되면 즉시 전체 중단 | 완전히 새 히스토리만 허용할 때 |

```
# 기본 (skip)
gitshuttle import --file shuttle.bundle

# force
gitshuttle import --file shuttle.bundle --on-conflict force

# abort
gitshuttle import --file shuttle.bundle --on-conflict abort
```

---

## 14. 자주 묻는 질문 (FAQ)

**Q. 실행 시 "Git 2.37 이상이 필요합니다" 오류가 납니다.**

Git 버전을 확인합니다:
```
git --version
```
2.37 미만이라면 [https://git-scm.com/download/win](https://git-scm.com/download/win) 에서 최신 버전을 설치합니다.

---

**Q. TUI 화면이 깨지거나 표시가 이상합니다.**

Windows Terminal 또는 PowerShell 7+ 사용을 권장합니다.  
CMD 환경에서는 다른 방식을 사용하세요:
```
gitshuttle export --ui csv
gitshuttle export --ui prompt
```

---

**Q. 한글 커밋 메시지나 파일명이 깨집니다.**

터미널 코드 페이지를 UTF-8로 변경합니다:
```
chcp 65001
gitshuttle export
```

또는 환경변수를 설정합니다:
```
set PYTHONUTF8=1
gitshuttle export
```

---

**Q. `[imported]` 표시된 커밋이 계속 나옵니다.**

`[imported]` 커밋은 이미 내부망에 반입된 것입니다. 선택하지 않고 그냥 넘어가세요.  
실수로 다시 import해도 `skip` 옵션(기본값)이 자동으로 건너뜁니다.

---

**Q. `gitshuttle.toml`은 어디에 두어야 하나요?**

두 위치 중 하나에 두면 됩니다:
- 작업 중인 Git 리포지토리 루트 폴더 (리포지토리별 설정, 권장)
- 홈 디렉터리 (`C:\Users\사용자명\`) (모든 리포지토리에 공통 적용)

같은 설정을 모든 프로젝트에 쓰고 싶으면 홈 디렉터리에, 프로젝트마다 다르게 쓰고 싶으면 각 리포지토리에 두세요.

---

**Q. bundle 파일이 너무 커서 USB에 안 들어갑니다.**

[분할 전송 기능](#10-대용량-파일-분할-전송)을 사용하세요.  
또는 커밋 수를 줄여 여러 번 나눠 export하세요.

---

**Q. `gitshuttle.exe`가 없는데 어떻게 실행하나요?**

현재 릴리즈 파일이 없을 경우 Python으로 직접 실행합니다:
```
python -m gitshuttle import --file shuttle.bundle
```
또는 PyInstaller가 설치된 환경에서 직접 빌드합니다:
```powershell
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File build.ps1
```

---

**Q. 다른 디렉터리에서 실행하면 `No module named gitshuttle` 오류가 납니다.**

타겟 리포 디렉터리에서 gitshuttle을 실행할 때 Python이 패키지를 찾지 못하는 경우입니다.
`PYTHONPATH`로 gitshuttle 소스 경로를 지정하세요:
```bash
cd /path/to/target-repo
PYTHONPATH=D:/cla/03_gitshuttle python -m gitshuttle import --file shuttle.bundle
```

---

**Q. import 후 커밋이 기존 main 브랜치에 바로 들어가지 않습니다.**

정상 동작입니다. GitShuttle은 소스의 `main`을 타겟의 기존 `main`에 직접 병합하지 않고, `imported/main` 같은 별도 브랜치에 격리합니다. 검토 후 직접 병합하세요:

```
git log imported/main --oneline
git merge imported/main
```

브랜치명을 직접 지정하려면 `--target-branch <이름>` 옵션을 사용합니다.

---

**Q. import한 커밋의 날짜가 모두 오늘 날짜입니다.**

기본 동작입니다(`--timestamp now`). 원본 날짜를 유지하려면:
```
gitshuttle import --file shuttle.bundle --timestamp original
```
또는 `gitshuttle.toml`에 `timestamp = "original"`로 설정합니다.

---

**Q. `.sha256` 파일 없이 import할 수 있나요?**

가능합니다. 체크섬 파일이 없으면 경고를 출력하고 검증 단계를 건너뜁니다.  
단, 파일 손상이나 변조를 감지하지 못합니다. 중요한 코드는 항상 3개 파일을 함께 이동하세요.

---

**Q. import 후 커밋이 안 보입니다.**

`git log --all --oneline` 명령어로 확인합니다.  
브랜치가 자동 병합되므로 `git log` 만으로는 안 보일 수 있습니다.

---

**Q. import 이력은 있는데 실제 파일이 폴더에 안 보입니다.**

rewrite import는 `git fast-import`로 먼저 ref와 object DB를 갱신합니다. 구버전에서는 이 단계 뒤 작업 폴더 checkout/reset이 자동으로 되지 않아, `git log <브랜치>`에는 이력이 보이지만 파일 탐색기에는 이전 상태가 보일 수 있었습니다.

최신 버전은 import 후 대상 브랜치로 checkout/reset 하여 파일까지 자동 갱신합니다. 이미 이 현상이 발생했다면 아래처럼 수동으로 맞출 수 있습니다:

```powershell
git -C C:\repos\target-gitshuttle switch migration/gitshuttle-20260610
git -C C:\repos\target-gitshuttle reset --hard migration/gitshuttle-20260610
```

작업 중인 변경 사항이 있다면 `reset --hard` 전에 반드시 commit 또는 stash 하세요.

---

**Q. 최근 1~2개 커밋만 export했더니 `bundle 검증 실패`가 납니다.**

일부 커밋만 선택한 bundle은 그 직전 부모 커밋을 prerequisite로 가집니다.  
따라서 대상 repo에 **원본 부모 커밋 SHA**가 이미 있어야 검증을 통과합니다.

작성자 변경(`--author-map`)이나 날짜 변경(`--timestamp now/from=...`)을 사용해 이전한 repo는 커밋 SHA가 원본과 달라집니다. 이 경우 대상 repo에 이전 이력이 있어 보여도 Git 입장에서는 원본 부모 SHA가 없으므로 최근 2개만 담은 증분 bundle이 실패할 수 있습니다.

최신 GitShuttle은 rewrite import가 끝난 뒤 원본 bundle refs를 `refs/gitshuttle/original/...` 숨김 영역에 보관합니다.
이 숨김 ref는 일반 브랜치처럼 작업하지 않지만, 다음 부분 bundle의 prerequisite 검증에 필요한 원본 부모 SHA를 대상 repo 안에 남겨 둡니다.

대상 repo의 기준점과 무관하게 강제로 이어붙이고 싶다면 `--bundle-scope full`로 self-contained bundle을 export한 뒤 `--on-conflict force --target-branch <브랜치>`로 import하세요.
이 방식은 bundle 파일이 커질 수 있지만 prerequisite 실패를 피합니다.

해결 방법:

```powershell
# 기준점 만들기: 필요한 전체 범위를 한 번 export/import
$env:GITSHUTTLE_HEADLESS = "1"
python -m gitshuttle export `
  --repo C:\repos\source-gitshuttle `
  --branch main `
  --ui tui `
  --output C:\transfer
Remove-Item Env:\GITSHUTTLE_HEADLESS

python -m gitshuttle import `
  --repo C:\repos\target-gitshuttle `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch migration/gitshuttle-full-v2 `
  --timestamp original
```

위 기준점 import 이후에는 최신 1~2개 커밋만 선택해 export한 bundle도 이어서 import할 수 있습니다.

구버전 GitShuttle로 이미 rewrite import한 repo는 숨김 원본 ref가 없을 수 있습니다. 이 경우 한 번은 전체 또는 필요한 기준 범위를 최신 버전으로 다시 import해야 이후 부분 증분이 안정적으로 이어집니다.

체리픽 형태로 변경분만 대상 브랜치 위에 재생하려면 `--format patchset`으로 export하고 `--mode replay`로 import하세요. 다만 이 방식은 원본 Git bundle 이력 이전과 다르게 커밋 SHA와 merge 구조가 달라질 수 있습니다.

---

## 15. 오류 메시지 해설

| 오류 메시지 | 원인 | 해결 방법 |
|-------------|------|-----------|
| `Git 2.37 이상이 필요합니다.` | Git 버전이 낮음 | [git-scm.com](https://git-scm.com)에서 최신 버전 설치 |
| `bundle 파일을 찾을 수 없습니다: ...` | 파일 경로가 잘못됨 | `--file` 뒤에 올바른 경로 입력 |
| `SHA-256 체크섬 불일치` | 파일 손상 또는 변조 | 외부망에서 재export 후 재전달 |
| `bundle 검증 실패` | bundle 손상 또는 부분 bundle의 prerequisite 커밋이 대상 repo에 없음 | 최근 일부 커밋만 export한 경우 대상 repo에 직전 원본 부모 커밋이 필요함. rewrite로 SHA가 바뀐 대상 repo라면 최신 버전으로 전체/기준 범위를 한 번 import해 `refs/gitshuttle/original/...` 기준점을 만든 뒤 증분 import |
| `이미 존재하는 커밋 N개 — abort` | `--on-conflict abort` 상태에서 중복 발견 | `--on-conflict skip` 또는 `force` 사용 |
| `선택된 커밋이 없습니다.` | export 시 아무 커밋도 선택하지 않음 | UI에서 커밋을 하나 이상 선택 후 재시도 |
| `현재 디렉터리에 Git 리포지토리가 없습니다.` | Git 리포지토리가 아닌 폴더에서 실행 | `cd` 로 올바른 폴더로 이동 후 재시도 |
| `bundle unbundle 실패` | bundle 사전 조건(prerequisite)을 만족 못 함 | 전체 히스토리 포함한 bundle로 재export |
| `Not updating refs/heads/... does not contain ...` | 대상 브랜치가 이미 있고 새 import 이력이 기존 tip을 포함하지 않음 | 다른 `--target-branch` 사용, 기존 로컬 브랜치 삭제, 또는 `--on-conflict force` 사용 |
| 이력은 있는데 파일이 안 보임 | ref/object는 갱신됐지만 작업 폴더가 target branch tip으로 갱신되지 않음 | 최신 버전 사용. 이미 발생했다면 `git switch <브랜치>` 후 `git reset --hard <브랜치>` |
| `replay patch 적용 실패`, `patch failed`, `already exists in index` | replay patch가 대상 브랜치의 현재 파일 상태와 충돌함 | 메시지의 실패 순번/원본 커밋/제목/git apply 상세를 확인. 이미 같은 변경분이면 자동 skip. 내용이 다르면 충돌 파일을 정리하거나 원본 변경 파일 우선 시 `--on-conflict force`로 재실행 |
| `작성자 매핑 파일을 찾을 수 없습니다: ...` | `--author-map` 경로가 잘못됨 | JSON 파일 경로 확인 |
| `타임스탬프 형식 오류: ...` | `from=` 모드에서 datetime 형식이 틀림 | `YYYY-MM-DDTHH:MM:SS` 형식으로 입력 |

---

## 16. 기존 GitHub에서 새 GitHub로 이전하기

하나의 GitHub 리포지토리에 있는 내용을 새로운 GitHub 리포지토리로 옮기면서, 커밋 작성자를 새 사용자로 바꾸는 절차입니다.

> **주의:** 커밋 사용자 변경은 Git 히스토리 재작성입니다. author/committer가 바뀌면 커밋 SHA도 바뀝니다.

### 목표 흐름

```
기존 GitHub repo
  → 로컬 source repo
  → GitShuttle export bundle
  → 로컬 target repo
  → author/committer rewrite import
  → 새 GitHub repo push
```

### 1단계. 원본 GitHub 리포지토리 clone

```powershell
git clone https://github.com/OLD_OWNER/OLD_REPO.git C:\repos\source-repo
```

예시:

```powershell
git clone https://github.com/ltw070/gitshuttle.git C:\repos\source-gitshuttle
```

### 2단계. 새 GitHub 리포지토리 clone

GitHub에서 빈 리포지토리를 먼저 만든 뒤 clone합니다.

```powershell
git clone https://github.com/NEW_OWNER/NEW_REPO.git C:\repos\target-repo
```

예시:

```powershell
git clone https://github.com/ltw070/new-gitshuttle.git C:\repos\target-gitshuttle
```

사내 GitHub 예시:

```powershell
git clone https://github.samsungds.net/tw070-lim/gitshuttle.git C:\repos\target-gitshuttle
```

### 3단계. GitShuttle로 원본 export

현재 터미널 위치가 원본 리포지토리가 아니어도 `--repo`로 원본 경로를 지정할 수 있습니다.

```powershell
cd D:\cla\03_gitshuttle

python -m gitshuttle export `
  --repo C:\repos\source-gitshuttle `
  --branch main `
  --ui tui `
  --output C:\transfer
```

현재 브랜치의 전체 이력을 TUI 선택 없이 bundle로 export하려면 `--full-branch`를 사용합니다.

```powershell
python -m gitshuttle export `
  --repo C:\repos\source-gitshuttle `
  --branch main `
  --full-branch `
  --output C:\transfer
```

TUI 동작을 유지한 채 조회된 커밋 전체를 자동 선택해야 하는 테스트·자동화 상황에서는 headless 환경변수를 사용할 수 있습니다.

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

### 4단계. 기존 작성자 목록 확인

원본 리포지토리에서 기존 커밋 작성자 이메일을 확인합니다.

```powershell
git -C C:\repos\source-gitshuttle log --all --format="%an <%ae>" | Sort-Object -Unique
```

### 5단계. 사용자 변경 매핑 파일 작성

`C:\transfer\author_map.json` 파일을 만듭니다.

```json
{
  "old@example.com": {
    "name": "ltw070",
    "email": "ltw070@naver.com"
  },
  "another-old@example.com": {
    "name": "ltw070",
    "email": "ltw070@naver.com"
  }
}
```

매핑 파일의 키는 `"Name <email>"` 형식이 아니라 **이메일 주소만** 써야 합니다.

### 6단계. 새 로컬 리포지토리에 import

```powershell
python -m gitshuttle import `
  --repo C:\repos\target-gitshuttle `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch imported/main `
  --timestamp original
```

날짜도 새 기준일로 바꾸려면 `--timestamp from=`을 사용합니다.

```powershell
# 2026-06-10 09:00 KST 기준 → UTC 2026-06-10 00:00 입력
python -m gitshuttle import `
  --repo C:\repos\target-gitshuttle `
  --file C:\transfer\shuttle_YYMMDD.bundle `
  --author-map C:\transfer\author_map.json `
  --target-branch imported/main `
  --timestamp from=2026-06-10T00:00:00
```

> `from=` 모드는 첫 커밋을 지정한 시각으로 맞추고, 이후 커밋은 원본 커밋 간 상대 간격을 유지합니다. 30분 고정 간격으로 재작성하는 기능은 현재 CLI 옵션에 포함되어 있지 않습니다.

### 7단계. import된 브랜치 확인

```powershell
git -C C:\repos\target-gitshuttle log imported/main --format="%h %an <%ae> %cn <%ce> %ad %s" --date=iso
```

현재 구현은 GitShuttle bundle의 `refs/gitshuttle/tmp_*` ref도 `--target-branch`로 지정한 브랜치에 맞춰 rewrite합니다.

### 8단계. 새 GitHub로 push

새 GitHub 리포지토리의 `main` 브랜치로 올립니다.

```powershell
cd C:\repos\target-gitshuttle
git push origin imported/main:main
```

새 GitHub 리포지토리가 비어 있지 않고 기존 이력이 있다면, 바로 `main`에 올리기보다 별도 브랜치로 먼저 올려 검토하는 것을 권장합니다.

```powershell
git push origin imported/main:gitshuttle-import
```

### 핵심 요약

| 목적 | 명령 |
|------|------|
| 원본 경로 지정 export | `gitshuttle export --repo C:\repos\source` |
| 대상 경로 지정 import | `gitshuttle import --repo C:\repos\target --file shuttle.bundle` |
| 사용자 변경 | `--author-map author_map.json` |
| 날짜 원본 유지 | `--timestamp original` |
| 날짜 기준점 변경 | `--timestamp from=YYYY-MM-DDTHH:MM:SS` |

커밋 author/committer 변경과 GitHub의 push actor는 별개입니다. GitHub 화면에서 push한 계정을 바꾸려면 실제 push 인증 계정 또는 PAT도 해당 사용자여야 합니다.

---

단계별 실습 예제: **[EXAMPLE.md](EXAMPLE.md)**

---

*GitShuttle v0.1.0 · Phase 1 (CLI + TUI) 완료*  
*문의: https://github.com/ltw070/gitshuttle/issues*
