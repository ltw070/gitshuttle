# GitShuttle

망분리(Air-Gapped) 환경에서 Git 리포지토리의 커밋 히스토리와 메타데이터를 완전히 보존하며 이전하는 CLI 도구입니다.

단순 소스 복사와 달리 커밋 메시지, 작성자, 상세 설명, 태그, 브랜치 히스토리를 그대로 유지합니다.

---

## 요구 사항

| 항목 | 버전 |
|------|------|
| OS | Windows (주 대상) |
| Git | 2.37 이상 |
| Python | 3.10 이상 (`.exe` 사용 시 불필요) |

---

## 설치 및 실행

### 방법 1 — 실행 파일 (권장)

`gitshuttle.exe`를 다운로드하여 원하는 경로에 배치합니다. Python 설치 불필요.

```
gitshuttle.exe export
gitshuttle.exe import --file shuttle_240522.bundle
gitshuttle.exe config
```

### 방법 2 — Python 직접 실행

```
pip install -r requirements.txt
python -m gitshuttle export
python -m gitshuttle import --file shuttle_240522.bundle
python -m gitshuttle config
```

---

## 기본 워크플로우

```
[외부망]  gitshuttle export
            → 커밋 목록에서 전송할 커밋 선택
            → shuttle_240522.bundle + .sha256 생성

[이동]    USB 또는 망간 전송 시스템으로 내부망 전달

[내부망]  gitshuttle import --file shuttle_240522.bundle
            → 체크섬 검증
            → 내부 Git 서버에 히스토리 그대로 반영
```

---

## 명령어

### `export` — 셔틀 패키지 생성

```
gitshuttle export [OPTIONS]

Options:
  --branch TEXT          대상 브랜치 (기본값: 현재 브랜치)
  --ui [tui|csv|html|prompt]
                         커밋 선택 UI 방식 (기본값: 설정 파일 또는 tui)
  --output TEXT          출력 파일명 (기본값: shuttle_YYMMDD.bundle)
```

**커밋 선택 UI 방식:**

| 옵션 | 방식 | 설명 |
|------|------|------|
| `tui` | TUI (기본값) | 터미널 인터랙티브 체크박스·테이블 |
| `csv` | CSV 편집 | `commits.csv` 생성 → Excel에서 `include` 컬럼 Y/N 수정 |
| `html` | Self-contained HTML | 브라우저에서 선택 → `selection.json` 다운로드 |
| `prompt` | InquirerPy | 방향키 + Space 멀티셀렉트 |

커밋 목록에서 이미 타겟 리포지토리에 반영된 커밋은 `[imported]`로 표시됩니다.

### `import` — 셔틀 패키지 반영

```
gitshuttle import --file FILE [OPTIONS]

Options:
  --file TEXT            .bundle 파일 경로 (필수)
  --on-conflict [skip|force|abort]
                         충돌 처리 방식 (기본값: skip)
```

**충돌 처리 옵션:**

| 옵션 | 동작 |
|------|------|
| `skip` (기본값) | 이미 존재하는 커밋은 건너뛰고 나머지 계속 진행 |
| `force` | 이미 존재해도 강제 덮어쓰기 |
| `abort` | 충돌 발견 즉시 전체 작업 중단 |

import 시 SHA-256 체크섬이 자동 검증됩니다. 불일치 시 작업이 중단되며 재export 명령어가 안내됩니다.

### `config` — 설정 마법사

```
gitshuttle config
```

`gitshuttle.toml`의 기본값을 대화형으로 변경합니다. 언제든 실행 가능.

---

## 설정 파일

`gitshuttle.toml`을 프로젝트 루트 또는 홈 디렉터리에 생성합니다.

```toml
[export]
ui = "tui"   # tui | csv | html | prompt
```

`--ui` 플래그는 설정 파일보다 항상 우선합니다.

---

## 생성 파일

| 파일 | 설명 |
|------|------|
| `shuttle_YYMMDD.bundle` | Git bundle 패키지 (압축 포함) |
| `shuttle_YYMMDD.sha256` | SHA-256 체크섬 |
| `shuttle_YYMMDD_manifest.txt` | 포함된 커밋 목록 요약 (심사용) |

---

## 개발 워크플로우 (기여자용)

모든 구현은 TDD Harness를 통해 진행합니다. 자세한 내용은 [`HARNESS.md`](HARNESS.md) 참고.

```
SubAgent1 (문서 정합성 검증)
  → SubAgent2 (TDD 구현)
    → SubAgent3 (테스트 검증) + SubAgent4 (규약 검증)  ← 병렬
```

SubAgent 정의 파일: `.claude/agents/`
