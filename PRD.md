# PRD: GitShuttle (Air-Gapped Git History Synchronizer)

## 1. 프로젝트 개요
GitShuttle은 서로 연결되지 않은 두 네트워크(내부망/외부망) 사이에서 Git 리포지토리의 변경 사항을 메타데이터(커밋 메시지, 설명, 작성자 등) 유실 없이 안전하게 나르는 '셔틀' 역할을 하는 도구입니다.

## 2. 목표 (Goals)
- 커밋 메시지, 상세 설명(Description), 태그, 브랜치 히스토리의 100% 무결성 유지.
- 네트워크가 단절된 환경에서도 증분(Incremental) 업데이트를 통한 효율적인 데이터 이전.
- 복잡한 Git 명령어를 몰라도 누구나 쉽게 반출입 패키지를 만들 수 있는 편의성 제공.

## 3. 핵심 기능 (Key Features)

### 3.1 히스토리 보존형 추출 (Full-Context Export)
- **Git Bundle 기술 활용:** 단순 소스 복사가 아닌, Git의 모든 객체(Objects)와 참조(Refs)를 포함하는 `.bundle` 파일 생성.
- **메타데이터 포함:** 각 커밋의 메시지(Subject), 상세 내용(Body), 작성자 정보, 커밋 시각을 그대로 유지.
- **커밋 단위 선택 추출:** 전체 브랜치 또는 특정 커밋을 개별 선택하여 패키징.

### 3.2 커밋 선택 인터페이스 (Phase 1 — 방식 비교)

Phase 1에서 커밋 선택은 아래 방식 중 하나(또는 조합)로 구현한다. 최종 방식은 구현 단계에서 확정.

| # | 방식 | 설명 | 장점 | 단점 |
|---|------|------|------|------|
| **A** ⭐ | **TUI (Textual)** — 기본값 | 터미널 안에서 체크박스·테이블 인터랙션 | 외부 앱 불필요, Shift 범위선택·필터 가능 | Windows 터미널 호환성 이슈 가능 |
| B | **CSV 편집** | `gitshuttle list > commits.csv` 생성 → Excel에서 `include` 컬럼 Y/N 수정 → `gitshuttle export --from commits.csv` | Excel 친화적, 비개발자도 직관적 | 파일 열고 저장하는 별도 단계 필요 |
| C | **Self-contained HTML** | 단일 `.html` 파일 생성 → 브라우저에서 열어 체크박스 선택 → "Export" 버튼으로 `selection.json` 다운로드 → `gitshuttle export --from selection.json` | 마우스 Shift 클릭·필터 완전 지원, 인터넷 불필요, Phase 2 GUI의 프리뷰 역할 | 2단계(브라우저 → CLI) 워크플로우 |
| D | **InquirerPy 멀티셀렉트** | 터미널에서 방향키 + Space로 선택 | 의존성 최소, 설치 간단 | 커밋 수 많을 때 불편, 필터 없음 |

**UI 방식 선택 메커니즘 — 2+3 조합:**

1. **설정 파일 (`gitshuttle.toml`)** — 기본값 고정. 미설정 시 A(TUI).
   ```toml
   [export]
   ui = "tui"   # tui | csv | html | prompt
   ```

2. **`--ui` 플래그** — 1회성 오버라이드. 설정 파일보다 항상 우선.
   ```
   gitshuttle export                  # 설정 파일 기본값 사용
   gitshuttle export --ui csv         # 이번 실행만 B
   gitshuttle export --ui html        # 이번 실행만 C
   gitshuttle export --ui prompt      # 이번 실행만 D
   ```

3. **`gitshuttle config` 마법사** — 언제든 실행해 설정 파일의 기본값을 변경.
   ```
   $ gitshuttle config

   커밋 선택 UI 기본값을 선택하세요:
     [1] TUI      — 터미널 인터랙티브 ← 현재 설정
     [2] CSV      — Excel 편집
     [3] HTML     — 브라우저
     [4] Prompt   — 방향키 멀티셀렉트

   선택 (1~4): _
   ```
   선택 결과는 `gitshuttle.toml`에 저장.

#### 공통 표시 사항 (방식 무관)
- 커밋 해시(short), 날짜, 작성자, 커밋 메시지, 변경 파일 수를 컬럼으로 표시.
- 이미 타겟 리포지토리에 반영된 커밋은 별도 표시(회색 또는 `[imported]` 태그)하여 중복 선택 방지.
- 작성자(Author), 파일 경로(File path), 날짜 범위 기준 필터링 제공.

### 3.3 셔틀 패키지 관리 (Shuttle Package)
- **압축:** 추출된 bundle 데이터를 압축하여 단일 패키지 파일로 생성.
- **매니페스트 생성:** 패키지 내부에 포함된 커밋 로그 요약본(Summary)을 텍스트 파일로 자동 생성하여, 반출입 심사 시 검토용으로 활용.
- **SHA-256 체크섬:** 패키지 생성 시 체크섬 파일을 함께 생성하여 전송 중 파일 변조·손상 검증.

### 3.4 스마트 복원 (Intelligent Import)
- **자동 커밋 매칭:** 타겟 리포지토리의 현재 상태와 패키지 내 커밋을 비교하여 신규 커밋만 선별 반영.
- **Fast-Forward 지원:** 히스토리가 깨지지 않도록 가능한 경우 Fast-forward 방식으로 병합 유도.
- **충돌 처리 — 3단계 옵션:**
  - `--on-conflict skip` (기본값): 이미 존재하는 커밋은 건너뛰고 나머지 계속 진행.
  - `--on-conflict force`: 이미 존재해도 강제 덮어쓰기.
  - `--on-conflict abort`: 충돌 발견 즉시 전체 작업 중단 (아무것도 반영하지 않음).

### 3.5 손상 파일 복구 (Error Recovery)
- import 시 SHA-256 체크섬 불일치가 발생하면 명확한 오류 메시지(기대값 vs 실제값)를 출력하고 작업을 중단.
- 복구 방법: 소스 측에서 동일 조건으로 재export하도록 안내 메시지와 재실행 명령어를 자동 출력.

## 4. 사용자 시나리오 (User Scenario)
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
| **TUI 라이브러리** | Textual 또는 Rich + prompt_toolkit (검토 필요) |
| **패키지 압축** | ZIP 또는 tar.gz |
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
- 대규모 리포지토리의 경우 분할 압축(Split archive) 기능 지원.

## 8. 개발 로드맵 (Phases)

### Phase 1 — CLI + TUI
- `gitshuttle export`: TUI 커밋 선택 인터페이스 포함
- `gitshuttle import`: 충돌 처리 옵션, 체크섬 검증 포함
- 매니페스트 자동 생성
- SHA-256 체크섬 생성/검증

### Phase 2 — GUI
- Phase 1의 모든 기능을 데스크탑 GUI로 전환
- 마우스 기반 커밋 선택, 드래그 범위 선택
- 시각적 히스토리 그래프 제공
