# GitShuttle 사용자 매뉴얼 (A to Z)

---

## 목차

1. [개요](#1-개요)
2. [설치](#2-설치)
3. [첫 실행 확인](#3-첫-실행-확인)
4. [기본 워크플로우 — 망분리 환경](#4-기본-워크플로우--망분리-환경)
5. [export — 셔틀 패키지 생성](#5-export--셔틀-패키지-생성)
6. [import — 셔틀 패키지 반입](#6-import--셔틀-패키지-반입)
7. [config — 설정 마법사](#7-config--설정-마법사)
8. [커밋 선택 UI 상세](#8-커밋-선택-ui-상세)
9. [생성 파일 설명](#9-생성-파일-설명)
10. [충돌 처리 옵션](#10-충돌-처리-옵션)
11. [sync — GitHub 직접 동기화 (Phase 2)](#11-sync--github-직접-동기화-phase-2)
12. [자주 묻는 질문 (FAQ)](#12-자주-묻는-질문-faq)
13. [오류 메시지 해설](#13-오류-메시지-해설)

---

## 1. 개요

**GitShuttle**은 인터넷이 없는 망분리(Air-Gapped) 환경에서 Git 리포지토리의 커밋 히스토리를 USB 등 물리 매체를 통해 안전하게 이전하는 CLI 도구입니다.

| 항목 | 내용 |
|------|------|
| 주 사용 환경 | Windows (CMD / PowerShell / Windows Terminal) |
| Git 요구 버전 | 2.37 이상 |
| Python | 3.10 이상 (`.exe` 사용 시 불필요) |

**핵심 특징**
- 커밋 메시지, 작성자, 상세 설명, 태그, 브랜치 히스토리 **100% 보존**
- 한글 커밋 메시지 완전 지원
- SHA-256 체크섬으로 전송 중 파일 변조/손상 자동 감지
- 이미 반입된 커밋 자동 감지 → 중복 작업 방지

---

## 2. 설치

### 방법 A — 실행 파일 (권장, Python 불필요)

1. `gitshuttle.exe` 파일을 다운로드합니다.
2. 원하는 경로(예: `C:\tools\`)에 복사합니다.
3. 해당 경로를 시스템 PATH에 추가하거나 전체 경로로 실행합니다.

```
C:\tools\gitshuttle.exe --help
```

### 방법 B — Python으로 직접 실행

```
pip install -r requirements.txt
python -m gitshuttle --help
```

### 설치 확인

```
gitshuttle --version
```

출력 예시: `gitshuttle version 0.1.0`

---

## 3. 첫 실행 확인

설치 후 아래 명령어로 정상 작동 여부를 확인합니다.

```
gitshuttle --help
```

```
Usage: gitshuttle [OPTIONS] COMMAND [ARGS]...

  GitShuttle: 망분리 환경을 위한 Git 히스토리 동기화 도구.

Commands:
  export  선택한 커밋을 .bundle 파일로 추출합니다.
  import  shuttle 패키지를 현재 리포지토리에 반입합니다.
  config  대화형 마법사로 gitshuttle.toml 설정을 변경합니다.
  sync    두 GitHub 리포지토리 간 직접 동기화합니다 (Phase 2).
```

---

## 4. 기본 워크플로우 — 망분리 환경

```
[외부망 PC]                        [USB 등 물리 매체]           [내부망 PC]
     │                                     │                         │
     │  1. gitshuttle export               │                         │
     │     커밋 선택 → 패키지 생성          │                         │
     │                                     │                         │
     │  2. 생성 파일 3종 복사 ─────────────▶│─────────────────────────▶│
     │     shuttle_YYMMDD.bundle           │                         │
     │     shuttle_YYMMDD.sha256           │                         │
     │     shuttle_YYMMDD_manifest.txt     │                         │
     │                                     │                         │
     │                                     │  3. gitshuttle import   │
     │                                     │     체크섬 검증          │
     │                                     │     히스토리 반영         │
```

### 단계별 설명

**외부망 작업**

```
cd C:\projects\my-repo
gitshuttle export
```

TUI 화면에서 전송할 커밋을 선택합니다.

**파일 이동**

생성된 3개 파일(`*.bundle`, `*.sha256`, `*_manifest.txt`)을 USB에 복사하여 내부망으로 전달합니다.

**내부망 작업**

```
cd C:\internal-repo
gitshuttle import --file D:\USB\shuttle_260508.bundle
```

---

## 5. export — 셔틀 패키지 생성

```
gitshuttle export [OPTIONS]
```

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--branch TEXT` | 추출할 브랜치 | 현재 브랜치 |
| `--ui [tui\|csv\|html\|prompt]` | 커밋 선택 UI 방식 | 설정 파일 또는 `tui` |
| `--output TEXT` | 출력 파일명 | `shuttle_YYMMDD.bundle` |

**예시**

```
# 기본 (TUI)
gitshuttle export

# 특정 브랜치
gitshuttle export --branch feature/login

# CSV 방식으로 선택
gitshuttle export --ui csv

# 출력 파일명 지정
gitshuttle export --output my_patch.bundle
```

**실행 흐름**

1. 현재 디렉터리의 Git 리포지토리에서 커밋 목록 읽기
2. 선택한 UI로 전송할 커밋 선택
3. 선택된 커밋으로 `.bundle` 파일 생성
4. SHA-256 체크섬(`.sha256`) 생성
5. 커밋 목록 요약(`_manifest.txt`) 생성

---

## 6. import — 셔틀 패키지 반입

```
gitshuttle import --file FILE [OPTIONS]
```

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--file TEXT` | `.bundle` 파일 경로 (필수) | — |
| `--on-conflict [skip\|force\|abort]` | 충돌 처리 방식 | `skip` |

**예시**

```
# 기본 (skip 방식)
gitshuttle import --file shuttle_260508.bundle

# USB에서 직접 반입
gitshuttle import --file D:\USB\shuttle_260508.bundle

# 충돌 시 강제 덮어쓰기
gitshuttle import --file shuttle_260508.bundle --on-conflict force

# 충돌 발견 즉시 전체 중단
gitshuttle import --file shuttle_260508.bundle --on-conflict abort
```

**실행 흐름**

1. `.sha256` 파일을 자동 탐색하여 체크섬 검증
2. 체크섬 일치 시 bundle 내 커밋을 현재 리포지토리와 비교
3. 신규 커밋만 선별하여 Fast-forward 방식으로 반영
4. 충돌 발생 시 `--on-conflict` 옵션에 따라 처리

**체크섬 불일치 시**

```
[오류] 체크섬 불일치
  기대값: a3f8c2d1...
  실제값: b9e4f7a2...

파일이 손상되었거나 변조되었습니다.
소스 측에서 아래 명령어로 재export 후 다시 전달해 주세요:
  gitshuttle export --branch main --output shuttle_260508.bundle
```

---

## 7. config — 설정 마법사

```
gitshuttle config
```

`gitshuttle.toml` 파일의 기본값을 대화형으로 변경합니다.

**실행 예시**

```
$ gitshuttle config

커밋 선택 UI 기본값을 선택하세요:
  [1] TUI      — 터미널 인터랙티브 ← 현재 설정
  [2] CSV      — Excel 편집
  [3] HTML     — 브라우저
  [4] Prompt   — 방향키 멀티셀렉트

선택 (1~4): 2

설정이 저장되었습니다: gitshuttle.toml
```

**설정 파일 위치 우선순위**

1. 현재 작업 디렉터리의 `gitshuttle.toml`
2. 홈 디렉터리(`~`)의 `gitshuttle.toml`
3. 하드코딩 기본값 (`tui`)

**gitshuttle.toml 직접 편집**

```toml
[export]
ui = "tui"   # tui | csv | html | prompt
```

---

## 8. 커밋 선택 UI 상세

### TUI (기본값) — 터미널 인터랙티브

Textual 기반 체크박스 테이블입니다.

```
┌────────────────────────────────────────────────────────────────┐
│ GitShuttle Export                              [Q] 종료  [E] Export │
├──────┬──────┬──────────────┬───────────┬──────────────────────┤
│  □   │ Hash │ 날짜          │ 작성자    │ 커밋 메시지          │
├──────┼──────┼──────────────┼───────────┼──────────────────────┤
│  □   │ a3f8 │ 2026-05-01   │ Alice     │ feat: 로그인 구현    │
│  □   │ b9e4 │ 2026-04-28   │ Bob       │ fix: 인코딩 수정     │
│  ✓   │ c2d1 │ 2026-04-25   │ Alice     │ [imported] init      │
└──────┴──────┴──────────────┴───────────┴──────────────────────┘
```

| 키 | 동작 |
|----|------|
| `Space` | 현재 행 선택/해제 |
| `Shift + ↓/↑` | 범위 선택 |
| `A` | 전체 선택 |
| `F` | 필터 (작성자/파일/날짜) |
| `E` | 선택 완료 후 Export |
| `Q` | 취소 |

이미 내부망에 반입된 커밋은 `[imported]`로 표시되며 기본 비선택 상태입니다.

---

### CSV 방식

```
gitshuttle export --ui csv
```

1. `commits.csv` 파일이 현재 디렉터리에 생성됩니다.
2. Excel 또는 메모장으로 파일을 열어 `include` 컬럼을 `Y`/`N`으로 편집합니다.
3. 저장 후 터미널에서 Enter를 누르면 export가 진행됩니다.

```csv
include,hash,date,author,message,files_changed
Y,a3f8c2d1,2026-05-01,Alice,feat: 로그인 구현,3
N,b9e4f7a2,2026-04-28,Bob,fix: 인코딩 수정,1
N,c2d1e9f3,2026-04-25,Alice,[imported] init,2
```

---

### HTML 방식

```
gitshuttle export --ui html
```

1. `commits_YYMMDD.html` 파일이 생성됩니다.
2. 브라우저로 파일을 열어 체크박스로 커밋을 선택합니다.
3. "Export" 버튼을 클릭하면 `selection.json`이 다운로드됩니다.
4. `selection.json`을 작업 디렉터리에 놓으면 export가 자동 진행됩니다.

인터넷 연결이 필요 없는 자급자족(self-contained) HTML입니다.

---

### Prompt 방식

```
gitshuttle export --ui prompt
```

터미널에서 방향키와 `Space`로 커밋을 선택합니다.

```
? 전송할 커밋을 선택하세요 (Space: 선택, Enter: 확인)
 ❯ ◉ a3f8 | 2026-05-01 | Alice     | feat: 로그인 구현
   ○ b9e4 | 2026-04-28 | Bob       | fix: 인코딩 수정
   ○ c2d1 | 2026-04-25 | Alice     | [imported] init
```

---

## 9. 생성 파일 설명

export 실행 시 아래 3개 파일이 생성됩니다.

| 파일 | 설명 | 용도 |
|------|------|------|
| `shuttle_YYMMDD.bundle` | Git bundle (압축 포함) | 히스토리 이전 핵심 파일 |
| `shuttle_YYMMDD.sha256` | SHA-256 체크섬 | 파일 무결성 검증 |
| `shuttle_YYMMDD_manifest.txt` | 포함된 커밋 목록 요약 | 반출입 심사용 |

**manifest.txt 예시**

```
GitShuttle Manifest
생성일시: 2026-05-08 14:30:00
브랜치: main
커밋 수: 3

a3f8c2d1  2026-05-01  Alice     feat: 로그인 구현          (3 files)
b9e4f7a2  2026-04-28  Bob       fix: 인코딩 수정           (1 file)
c2d1e9f3  2026-04-25  Alice     docs: README 작성          (2 files)
```

**3개 파일을 반드시 함께 이동하세요.** `.sha256` 없이 import 시 체크섬 검증이 생략됩니다.

---

## 10. 충돌 처리 옵션

| 옵션 | 동작 | 권장 사용 상황 |
|------|------|----------------|
| `skip` (기본값) | 이미 존재하는 커밋은 건너뛰고 나머지 계속 | 증분 업데이트 |
| `force` | 이미 존재해도 강제 덮어쓰기 | 히스토리 재정렬이 필요할 때 |
| `abort` | 충돌 발견 즉시 전체 작업 중단 | 완전히 새로운 히스토리만 허용할 때 |

---

## 11. sync — GitHub 직접 동기화 (Phase 2)

> **Phase 2 기능입니다.** 네트워크가 연결된 환경에서만 사용 가능합니다.

두 GitHub 리포지토리 사이에서 파일 없이 직접 커밋을 동기화합니다.

```
gitshuttle sync [--on-conflict skip|force|abort]
```

### 사전 설정

```
gitshuttle config
```

`gitshuttle.toml`에 source/target 정보를 입력합니다.

```toml
[sync.source]
url  = "https://github.com/org1/repo"
auth = "token"   # token | ssh

[sync.target]
url  = "https://github.com/org2/repo"
auth = "token"
```

**토큰은 환경변수로 전달합니다 (파일에 직접 저장 금지).**

```
set GS_SOURCE_TOKEN=ghp_xxxxxxxxxxxx
set GS_TARGET_TOKEN=ghp_yyyyyyyyyyyy
gitshuttle sync
```

### SSH 방식

```toml
[sync.source]
url     = "git@github.com:org1/repo.git"
auth    = "ssh"
ssh_key = "C:\\Users\\user\\.ssh\\id_rsa_source"
```

### 실행 흐름

1. Source repo에서 커밋 목록 fetch
2. Target repo의 현재 상태와 비교 (`[synced]` 표시)
3. TUI/CSV/HTML/Prompt로 전송할 커밋 선택
4. 선택 커밋을 Source에서 fetch → Target으로 push

---

## 12. 자주 묻는 질문 (FAQ)

**Q. 이미 반입한 커밋이 또 표시됩니다.**

A. `[imported]` 표시가 있는 커밋은 이미 내부망에 반영된 것입니다. 선택 해제 후 export하세요. `--on-conflict skip`(기본값) 옵션을 사용하면 중복 import도 안전하게 처리됩니다.

**Q. TUI 화면이 깨져 보입니다.**

A. Windows Terminal 또는 PowerShell 7+ 사용을 권장합니다. CMD 환경에서는 `--ui csv` 또는 `--ui prompt` 방식을 사용하세요.

```
gitshuttle export --ui prompt
```

**Q. 한글 커밋 메시지가 깨집니다.**

A. 터미널의 코드 페이지를 UTF-8로 변경합니다.

```
chcp 65001
gitshuttle export
```

또는 환경변수를 설정합니다.

```
set PYTHONUTF8=1
gitshuttle export
```

**Q. `gitshuttle.toml`은 어디에 두어야 하나요?**

A. 작업 중인 Git 리포지토리 루트 또는 홈 디렉터리(`C:\Users\사용자명\`)에 두면 됩니다. 리포지토리별 설정은 리포지토리 루트에 두는 것을 권장합니다.

**Q. 대용량 리포지토리에서 bundle 파일이 너무 큽니다.**

A. 분할 압축 기능(Sprint 5에서 구현 예정)을 사용하면 자동으로 분할/재조립됩니다. 현재 버전에서는 커밋 수를 줄여서 여러 번 나눠 export하세요.

**Q. `.sha256` 파일 없이 import할 수 있나요?**

A. 가능하지만 권장하지 않습니다. 체크섬 검증이 생략되어 파일 손상/변조를 감지할 수 없습니다.

---

## 13. 오류 메시지 해설

| 오류 메시지 | 원인 | 해결 방법 |
|-------------|------|-----------|
| `Git 2.37 이상이 필요합니다.` | 설치된 Git 버전이 낮음 | Git 업그레이드 |
| `체크섬 불일치` | 파일 손상/변조 | 소스 측에서 재export 후 재전달 |
| `bundle 검증 실패` | bundle 파일 손상 | 파일을 다시 전달받아 재시도 |
| `현재 디렉터리에 Git 리포지토리가 없습니다.` | Git 초기화 안 됨 | `git init` 또는 올바른 디렉터리로 이동 |
| `선택된 커밋이 없습니다.` | export 시 아무것도 선택 안 함 | UI에서 커밋 선택 후 재시도 |
| `충돌 감지 — abort` | `--on-conflict abort` 옵션에서 충돌 발생 | `skip` 또는 `force` 옵션으로 재시도 |

---

*GitShuttle v0.1.0 | Phase 1 (CLI + TUI)*
