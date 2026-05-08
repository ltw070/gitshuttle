# REPORT.md — GitShuttle 작업 기록

---

## 2026-05-08

### 1. PRD 작성
- `PRD.md` 초안 작성 (프로젝트 개요, 목표, 핵심 기능, 사용자 시나리오)
- 보완 항목 식별 및 반영:
  - 비기능 요건 추가 (Windows, Git 2.37+, Python 3.10+)
  - 충돌 처리 3단계 옵션 (`skip` / `force` / `abort`)
  - 암호화 요건 제거
  - 손상 파일 복구 방식 정의 (SHA-256 불일치 → 재export 안내)

### 2. 커밋 선택 UI 방식 설계
- A~D 4가지 방식 비교 테이블 작성:
  - **A. TUI (Textual)** — 기본값
  - **B. CSV 편집** — Excel 친화적
  - **C. Self-contained HTML** — 브라우저 선택 → selection.json
  - **D. InquirerPy** — 방향키 + Space
- UI 방식 선택 메커니즘 확정:
  - 설정 파일 `gitshuttle.toml` + `--ui` 플래그 + `gitshuttle config` 마법사 조합

### 3. 배포 방식 결정
- 주 배포: `gitshuttle.exe` (PyInstaller, Python 불필요)
- 보조 실행: `python -m gitshuttle`
- 엔트리포인트: `gitshuttle/__main__.py`

### 4. 개발 로드맵 확정
- Phase 1: CLI + TUI
- Phase 2: 데스크탑 GUI

### 5. 문서 생성
- `README.md`: 사용자 대상 — 설치, 명령어, 워크플로우, 설정
- `CLAUDE.md`: Claude Code 대상 — 기술 스택, 엔트리포인트, 제약 사항

### 6. Git 저장소 초기화 및 GitHub 연결
- 로컬 git init, main 브랜치 설정
- 인코딩 설정:
  - `git config core.quotepath false`
  - `git config i18n.commitEncoding utf-8`
  - `git config i18n.logOutputEncoding utf-8`
  - `.gitattributes` 생성 (UTF-8 + LF)
- GitHub private repo 생성: `https://github.com/ltw070/gitshuttle`
- remote 연결 및 push 완료

### 7. TDD Harness 설계 및 구현
- `.claude/agents/` 에 4개 SubAgent 정의 파일 생성:

  | 파일 | 역할 | 실행 순서 |
  |------|------|-----------|
  | `subagent1-doc-verify.md` | PRD↔README↔CLAUDE.md 정합성 검증 (6개 항목) | 1번 (단독) |
  | `subagent2-ai-action.md` | TDD 구현 (RED→GREEN→REFACTOR) | 2번 (단독) |
  | `subagent3-test-verify.md` | pytest + 커버리지 + 회귀 검사 | 3번 (SA4와 병렬) |
  | `subagent4-compliance-verify.md` | 인코딩·네트워크·Phase범위·PEP8 검사 | 3번 (SA3와 병렬) |

- `HARNESS.md` 생성: 오케스트레이션 흐름 전체 문서화

---

### 8. TDD 개발 계획 수립
- `PLAN.md` 생성: Phase 1을 Sprint 0~6으로 분리, 각 Sprint에 SA 호출 프롬프트 포함
- `CLAUDE.md` 업데이트: 패키지 구조 목표, 브랜치 전략 추가
- 브랜치 전략: `sprint/0-scaffold` ~ `sprint/6-build` → `main` merge

---

## 다음 작업 (Next)

- [ ] `sprint/0-scaffold` 브랜치 생성
- [ ] SA1 실행 → 문서 정합성 검증
- [ ] SA2 실행 → Sprint 0 구현 (`pyproject.toml`, 패키지 스캐폴딩, `conftest.py`)
- [ ] SA3+SA4 병렬 실행 → 검증 후 `main` merge
