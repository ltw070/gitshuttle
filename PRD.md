# PRD: GitShuttle (Air-Gapped Git History Synchronizer)

## 1. 프로젝트 개요
GitShuttle은 서로 연결되지 않은 두 네트워크(내부망/외부망) 사이에서 Git 리포지토리의 변경 사항을 메타데이터(커밋 메시지, 설명, 작성자 등) 유실 없이 안전하게 나르는 '셔틀' 역할을 하는 도구입니다.

## 2. 목표 (Goals)
- 선택한 브랜치/커밋 범위의 커밋 메시지, 상세 설명(Description), 작성자, 파일 이력 무결성 유지.
- 네트워크가 단절된 환경에서도 증분(Incremental) 업데이트를 통한 효율적인 데이터 이전.
- 복잡한 Git 명령어를 몰라도 누구나 쉽게 반출입 패키지를 만들 수 있는 편의성 제공.

## 3. 핵심 기능 (Key Features)

### 3.1 히스토리 보존형 추출 (Full-Context Export)
- **Git Bundle 기술 활용:** 단순 소스 복사가 아닌, 선택한 tip 또는 범위에서 도달 가능한 Git 객체를 `.bundle` 파일로 생성.
- **메타데이터 포함:** 각 커밋의 메시지(Subject), 상세 내용(Body), 작성자 정보, 커밋 시각을 그대로 유지.
- **커밋 단위 선택 추출:** 전체 브랜치 또는 특정 커밋을 개별 선택하여 패키징.

### 3.2 커밋 선택 인터페이스

커밋 선택은 주력 TUI와 보조 CSV 방식으로 제공한다.

| # | 방식 | 설명 | 장점 | 단점 |
|---|------|------|------|------|
| **A** ⭐ | **TUI (Textual)** — 기본값 | 터미널 안에서 체크박스·테이블 인터랙션 | 외부 앱 불필요, 방향키/Space/A/E 조작 가능 | Windows 터미널 호환성 이슈 가능 |
| B | **CSV 편집** | `commits.csv` 생성 → Excel에서 `include` 컬럼 Y/N 수정 | Excel 친화적, 비개발자도 직관적 | 파일 열고 저장하는 별도 단계 필요 |

**UI 방식 선택 메커니즘 — 2+3 조합:**

1. **설정 파일 (`gitshuttle.toml`)** — 기본값 고정. 미설정 시 A(TUI).
   ```toml
   [export]
   ui = "tui"   # tui | csv
   ```

2. **`--ui` 플래그** — 1회성 오버라이드. 설정 파일보다 항상 우선.
   ```
   gitshuttle export                  # 설정 파일 기본값 사용
   gitshuttle export --ui csv         # 이번 실행만 B
   ```

3. **`gitshuttle config` 마법사** — 언제든 실행해 설정 파일의 기본값을 변경.
   ```
   $ gitshuttle config

   커밋 선택 UI 기본값을 선택하세요:
     [1] TUI      — 터미널 인터랙티브 ← 현재 설정
     [2] CSV      — Excel 편집

   선택 (1~2): _
   ```
   선택 결과는 `gitshuttle.toml`에 저장.

#### 공통 표시 사항 (방식 무관)
- 커밋 해시(short), 날짜, 작성자, 커밋 메시지, 변경 파일 수를 컬럼으로 표시.
- CSV는 Excel 호환을 위해 UTF-8 BOM(`utf-8-sig`)으로 생성.

### 3.3 셔틀 패키지 관리 (Shuttle Package)
- **Git bundle:** 선택한 이력을 `.bundle` 파일로 생성한다.
- **매니페스트 생성:** 패키지 내부에 포함된 커밋 로그 요약본(Summary)을 텍스트 파일로 자동 생성하여, 반출입 심사 시 검토용으로 활용.
- **SHA-256 체크섬:** 패키지 생성 시 체크섬 파일을 함께 생성하여 전송 중 파일 변조·손상 검증.

### 3.4 스마트 반입 (Intelligent Import)
- **체크섬 검증:** `.bundle.sha256` 파일이 있으면 import 전에 SHA-256을 검증한다.
- **중복 감지:** 타겟 리포지토리의 기존 커밋과 bundle tip을 비교해 `skip|force|abort` 정책을 적용한다.
- **일반 import:** rewrite 옵션이 없으면 bundle 객체를 풀고 현재 브랜치로 fast-forward 또는 merge를 시도한다.
- **rewrite import:** 작성자/시간/브랜치 재작성이 필요하면 `fast-export | rewrite | fast-import` 파이프라인으로 대상 브랜치에 반영한다.
- **충돌 처리 — 3단계 옵션:**
  - `--on-conflict skip` (기본값): 이미 존재하는 커밋은 건너뛰고 나머지 계속 진행.
  - `--on-conflict force`: 이미 존재해도 강제 덮어쓰기.
  - `--on-conflict abort`: 충돌 발견 즉시 전체 작업 중단 (아무것도 반영하지 않음).

### 3.5 손상 파일 복구 (Error Recovery)
- import 시 SHA-256 체크섬 불일치가 발생하면 명확한 오류 메시지(기대값 vs 실제값)를 출력하고 작업을 중단.
- 복구 방법: 소스 측에서 동일 조건으로 재export하도록 안내 메시지와 재실행 명령어를 자동 출력.

### 3.6 Import-time Rewrite — 작성자 매핑 · 브랜치 격리 · 타임스탬프 (Phase 1 추가)

리포지토리가 다를 경우 import 시점에 작성자 정보·브랜치·타임스탬프를 재작성하여 타겟 조직의 규칙에 맞게 반영한다.

#### 3.6.1 작성자 매핑 (Author Mapping)

- **문제:** 소스 repo의 커밋 작성자(이름·이메일)가 타겟 조직의 내부 계정과 다름.
- **기능:** import 시 `--author-map <파일>` 플래그 또는 `gitshuttle.toml`의 `[import] author_map = "<파일>"` 설정으로 작성자 일괄 대체.
- **매핑 형식 (JSON):**
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
- **toml 설정 형식:**
  ```toml
  [import]
  author_map = "C:\\transfer\\author_map.json"
  ```
- **구현:** `git fast-export | (작성자 치환) | git fast-import` 파이프라인 사용.
- **미매핑 처리:** 매핑 테이블에 없는 작성자는 원본 그대로 유지 (경고 메시지 출력).

#### 3.6.2 브랜치 격리 (Branch Isolation)

- **정책:** 소스의 `main`/`master`를 타겟의 기존 `main`/`master`에 **직접 병합하지 않는다.**
  타겟 repo에 **별도 브랜치**를 새로 만들어 커밋을 반영하여, 타겟의 기본 브랜치를 보호한다.
- **기능:**
  - `--target-branch <이름>`: import된 커밋을 담을 신규 브랜치명 지정.
  - rewrite import에서 미지정 시 기본값: `imported/<소스브랜치명>` (예: `imported/main`, `imported/master`).
  - rewrite 옵션 없이 `gitshuttle import --file ...`만 실행하면 현재 브랜치로 merge를 시도한다.
  - 해당 브랜치가 타겟에 이미 존재하면 `--on-conflict` 옵션 정책을 따름.
  - 기존 기본 브랜치에 코드가 있는 경우, `migration/<소스브랜치>` 같은 별도 브랜치에 먼저 import하고 사용자가 검토 후 직접 merge할 수 있어야 함.
  - 별도 브랜치 import는 기존 기본 브랜치 ref를 이동시키지 않아야 하며, merge 시 동일 파일 충돌은 Git conflict로 드러나 사용자가 해결할 수 있어야 함.
  - 권장 사용 구조:
    ```
    main 쪽:       X -> Y -------- M
                                /
    import 쪽:        A -> B -> C
    ```
  - `Y`와 `A`가 직접 연결되는 것이 아니라, merge commit `M`이 `Y`와 `C`를 부모로 가지면서 두 이력을 연결함.
- **CLI 예시:**
  ```
  gitshuttle import --file shuttle.bundle
  # → 타겟에 imported/main 브랜치 생성

  gitshuttle import --file shuttle.bundle --target-branch ext-main
  # → 타겟에 ext-main 브랜치 생성

  gitshuttle import --file shuttle.bundle --target-branch migration/source-main
  git switch main
  git merge migration/source-main --allow-unrelated-histories
  # → 기존 main을 보존한 채 검토 후 병합
  ```
- **구현:** fast-import 시 ref를 `refs/heads/<target-branch>`로 지정.

#### 3.6.3 커밋 타임스탬프 (Commit Timestamp)

- **문제:** import된 커밋에 어떤 시간을 기록할지 용도에 따라 다름.
  - 반영시간: 타겟 repo 관리자 입장에서 언제 들어왔는지 추적 가능.
  - 원본시간: 소스에서의 개발 흐름을 그대로 보존.
  - 특정 시점 시작: 보안 감사·반입 심사 기준일을 기점으로 기록.

- **`--timestamp` 옵션 (3가지 모드):**

  | 값 | 설명 | 예시 |
  |----|------|------|
  | `now` (기본값) | 모든 커밋의 committer date를 import 실행 시각으로 통일 | - |
  | `original` | 소스의 author date·committer date 원본 그대로 보존 | `--timestamp original` |
  | `from=<datetime>` | 가장 오래된 커밋을 지정 시각으로 맞추고, 이후 커밋은 원본 상대 간격 유지 | `--timestamp from=2024-01-01T09:00:00` |

- **`from=<datetime>` 동작 상세:**
  - 선택된 커밋들을 오래된 순으로 정렬.
  - 가장 오래된 커밋의 committer date = `<datetime>`.
  - 나머지 커밋 = `<datetime>` + (원본 커밋과 최초 커밋 간의 시간 차이).
  - author date는 committer date와 동일하게 설정.
  - datetime 형식: ISO 8601 (`YYYY-MM-DDTHH:MM:SS`, 타임존 생략 시 UTC로 해석).

- **toml 설정:**
  ```toml
  [import]
  timestamp = "now"          # now | original | from=2024-01-01T09:00:00
  ```

#### 3.6.4 결합 사용 예시

```
# 작성자 매핑 + 별도 브랜치 생성 + 반입 기준일부터 타임스탬프
gitshuttle import \
  --file shuttle_240522.bundle \
  --author-map author_map.json \
  --target-branch ext-main \
  --timestamp from=2024-05-22T09:00:00

# 원본 시간 보존
gitshuttle import \
  --file shuttle_240522.bundle \
  --timestamp original
```

#### 3.6.5 명령어 옵션 요약

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--author-map <파일>` | 작성자 매핑 JSON 파일 경로 | 없음 (원본 유지) |
| `--target-branch <이름>` | rewrite import 커밋을 담을 브랜치명 | rewrite 시 `imported/<소스브랜치명>` |
| `--timestamp now\|original\|from=<dt>` | 커밋 타임스탬프 모드 | `now` |

---

#### 3.6.6 기준 브랜치 이후 변경분 이전 (Base Branch Delta)

- **목표:** 이미 존재하는 기본 브랜치에서 파생된 feature 브랜치의 신규 커밋만 대상 repo 브랜치 위에 이어붙인다.
- **CLI:** `gitshuttle export --branch <feature> --base-branch <base> --full-branch`
- **선택 범위:** `<base>..<feature>` 커밋 전체를 UI 없이 선택한다.
- **bundle 구조:**
  - 대상 repo가 원본 `<base>` SHA를 갖고 있지 않아도 `git bundle verify`가 통과해야 한다.
  - 이를 위해 export는 기준점 metadata ref(`refs/gitshuttle/base/...`)를 bundle에 함께 담은 self-contained bundle을 만든다.
  - import는 metadata ref를 fast-export 대상에서 제외하고, 제외된 parent SHA를 대상 브랜치의 현재 tip SHA로 치환한다.
- **결과:** bundle 파일은 일반 range bundle보다 커질 수 있지만, 대상 브랜치에는 `<base>..<feature>` 신규 커밋만 반영된다.
- **호환성:** metadata가 없는 구버전 `--base-branch` bundle은 대상 repo가 원본 base SHA를 갖고 있지 않으면 검증 실패할 수 있으며, 최신 버전으로 다시 export해야 한다.

## 4. 사용자 시나리오 (User Scenario)

### 시나리오 A — 망분리 환경 (파일 이동)
1. **[외부망]** 개발자가 `gitshuttle export` 실행 → TUI 커밋 목록에서 전송할 커밋을 선택.
2. **[GitShuttle]** 선택된 커밋과 전체 메타데이터를 포함한 `shuttle_240522.bundle` + 체크섬 파일 생성.
3. **[이동]** 보안 승인 후 해당 파일들을 USB나 망간 전송 시스템으로 내부망 전달.
4. **[내부망]** 담당자가 `gitshuttle import --file shuttle_240522.bundle` 실행.
5. **[결과]** 내부 Git 서버에 외부와 동일한 커밋 메시지와 히스토리가 그대로 반영됨.

## 5. 기술 스펙 (Technical Specification)

| 항목 | 내용 |
|------|------|
| **운영 환경** | Windows (주 대상) |
| **지원 Git 버전** | 2.37 이상 (2022년 이후 릴리즈 기준) |
| **Python 버전** | 3.10 이상 |
| **TUI 라이브러리** | Textual |
| **패키지 형식** | Git bundle + optional split parts |
| **무결성 검증** | SHA-256 체크섬 |

## 6. 배포 및 실행 방식 (Distribution)

### 주 배포: 단일 실행 파일 (`.exe`)
- PyInstaller로 빌드한 `gitshuttle.exe` 단일 파일로 배포.
- Python 설치 불필요 — Windows에서 바로 실행.
- USB 또는 망간 전송 시 셔틀 패키지와 함께 동봉 가능.

```
gitshuttle.exe export
gitshuttle.exe import --file shuttle_240522.bundle
gitshuttle.exe config
```

### 보조 실행: Python 직접 실행
- Python 3.10+ 환경에서 소스로 직접 실행 가능.

```
python -m gitshuttle export
python -m gitshuttle import --file shuttle_240522.bundle
python -m gitshuttle config
```

## 7. 대용량 처리
- 대규모 리포지토리의 경우 bundle 분할 전송(Split archive) 기능 지원.

## 8. 현재 제공 범위

- `gitshuttle export`: TUI/CSV 커밋 선택, `--recent`, `--full-branch`, `--base-branch` 기반 self-contained branch delta, bundle/manifest/checksum 생성
- `gitshuttle import`: SHA-256 검증, 일반 merge import, 작성자/타임스탬프 rewrite, 부분 bundle prerequisite/base metadata 제외 반입, rewrite 기반 대상 브랜치 반입, 충돌 처리
- 대용량 전송: bundle 분할/병합 지원
