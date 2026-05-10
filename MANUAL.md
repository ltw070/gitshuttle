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
| `--branch TEXT` | 특정 브랜치의 커밋만 추출 | `--branch feature/login` |
| `--ui [tui\|csv\|html\|prompt]` | 커밋 선택 방식 | `--ui csv` |
| `--output TEXT` | 출력 파일명 지정 | `--output patch_v2.bundle` |

### 실행 예시

```
# 기본 (현재 브랜치, TUI 방식)
gitshuttle export

# main 브랜치만
gitshuttle export --branch main

# CSV 방식으로 Excel에서 선택
gitshuttle export --ui csv

# 파일명을 직접 지정
gitshuttle export --output 기능개선_패치.bundle
```

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
| `--file TEXT` | bundle 파일 경로 **(필수)** | — |
| `--on-conflict [skip\|force\|abort]` | 충돌 처리 방식 | `skip` |
| `--author-map FILE` | 작성자 매핑 JSON 파일 경로 | 없음 (원본 유지) |
| `--target-branch TEXT` | import 커밋을 담을 브랜치명 | `imported/<소스브랜치>` |
| `--timestamp TEXT` | 커밋 타임스탬프 모드 | `now` |

### 실행 예시

```
# USB에서 반입 (기본: 중복 커밋은 건너뜀)
gitshuttle import --file D:\USB\shuttle_260508.bundle

# 현재 폴더에 있는 bundle 파일
gitshuttle import --file shuttle_260508.bundle

# 충돌 시 강제 덮어쓰기
gitshuttle import --file shuttle_260508.bundle --on-conflict force

# 중복 커밋 발견 즉시 전체 중단
gitshuttle import --file shuttle_260508.bundle --on-conflict abort
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

---

### 작성자 매핑 (Author Mapping)

소스 repo의 커밋 작성자를 타겟 조직의 내부 계정으로 대체합니다.

**1. 매핑 파일 작성 (`author_map.json`):**

```json
{
  "Jane Doe <jane@external.com>": "홍길동 <hong@internal.com>",
  "Bob Smith <bob@external.com>": "이철수 <lee@internal.com>"
}
```

**2. import 실행:**

```
gitshuttle import --file shuttle_260508.bundle --author-map author_map.json
```

- 매핑 테이블에 없는 작성자는 원본 그대로 유지되며 경고 메시지가 출력됩니다.
- `gitshuttle.toml`에 기본값으로 저장할 수 있습니다:

```toml
[import.author_map]
"Jane Doe <jane@external.com>" = "홍길동 <hong@internal.com>"
"Bob Smith <bob@external.com>" = "이철수 <lee@internal.com>"
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
from gitshuttle.sync_ import run_sync

result = run_sync(
    source_url="https://github.com/org1/repo",
    target_url="https://github.com/org2/repo",
    source_token="ghp_xxxx",   # 또는 환경변수 GS_SOURCE_TOKEN
    target_token="ghp_yyyy",   # 또는 환경변수 GS_TARGET_TOKEN
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
| `force` | 이미 존재해도 오류 없이 계속 진행 | 히스토리를 확실히 덮어써야 할 때 |
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

## 15. 오류 메시지 해설

| 오류 메시지 | 원인 | 해결 방법 |
|-------------|------|-----------|
| `Git 2.37 이상이 필요합니다.` | Git 버전이 낮음 | [git-scm.com](https://git-scm.com)에서 최신 버전 설치 |
| `bundle 파일을 찾을 수 없습니다: ...` | 파일 경로가 잘못됨 | `--file` 뒤에 올바른 경로 입력 |
| `SHA-256 체크섬 불일치` | 파일 손상 또는 변조 | 외부망에서 재export 후 재전달 |
| `bundle 검증 실패` | bundle 파일이 손상됨 | 파일 재전달 요청 |
| `이미 존재하는 커밋 N개 — abort` | `--on-conflict abort` 상태에서 중복 발견 | `--on-conflict skip` 또는 `force` 사용 |
| `선택된 커밋이 없습니다.` | export 시 아무 커밋도 선택하지 않음 | UI에서 커밋을 하나 이상 선택 후 재시도 |
| `현재 디렉터리에 Git 리포지토리가 없습니다.` | Git 리포지토리가 아닌 폴더에서 실행 | `cd` 로 올바른 폴더로 이동 후 재시도 |
| `bundle unbundle 실패` | bundle 사전 조건(prerequisite)을 만족 못 함 | 전체 히스토리 포함한 bundle로 재export |
| `작성자 매핑 파일을 찾을 수 없습니다: ...` | `--author-map` 경로가 잘못됨 | JSON 파일 경로 확인 |
| `타임스탬프 형식 오류: ...` | `from=` 모드에서 datetime 형식이 틀림 | `YYYY-MM-DDTHH:MM:SS` 형식으로 입력 |

---

단계별 실습 예제: **[EXAMPLE.md](EXAMPLE.md)**

---

*GitShuttle v0.1.0 · Phase 1 (CLI + TUI) 완료*  
*문의: https://github.com/ltw070/gitshuttle/issues*
