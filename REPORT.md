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

### 9. GitHub MCP 스킬 및 보안 설정
- `.claude/commands/github-mcp-setup.md` 생성: `/github-mcp-setup` 스킬 — 토큰 입력 → `.mcp.json` 자동 생성
- `.mcp.json.example` 생성: 토큰 없는 참고용 템플릿
- `.mcp.json` 초기 양식(플레이스홀더) 커밋 후 `.gitignore` 등록 및 추적 해제
- `.gitignore` 생성: `.mcp.json`, Python, PyInstaller, IDE 패턴 포함

---

### 10. Direct Sync 기능 추가 (Phase 2)
- **배경:** 단일 망 환경에서 두 GitHub repo 간 파일 없이 직접 동기화 요구
- **PRD 3.6** 신규 추가: Direct Sync 스펙, 인증 방식(HTTPS+Token / SSH), `gitshuttle.toml` 설정 구조
- **PRD 시나리오 B** 추가: `gitshuttle sync` 워크플로우
- **PLAN Sprint 7** 추가: `github_auth.py`, `sync_.py`, 환경변수 인증(`GS_SOURCE_TOKEN` / `GS_TARGET_TOKEN`)
- **README** 업데이트: `sync` 명령어 레퍼런스, HTTPS Token / SSH 설정 예시
- **CLAUDE.md** 업데이트: 명령어 구조에 `sync` 추가, 패키지 구조에 `sync_.py` / `github_auth.py` 추가

주요 설계 결정:
- Source / Target 각각 별도 인증 (다른 계정/조직 지원)
- 토큰은 파일에 저장 금지 → 환경변수(`GS_SOURCE_TOKEN`, `GS_TARGET_TOKEN`)로만 주입
- export/import와 동일한 커밋 선택 UI 재사용 (코드 중복 없음)

---

## 최종 저장소 현황 (2026-05-08 기준)

```
gitshuttle/
├── .claude/
│   ├── agents/
│   │   ├── subagent1-doc-verify.md
│   │   ├── subagent2-ai-action.md
│   │   ├── subagent3-test-verify.md
│   │   └── subagent4-compliance-verify.md
│   └── commands/
│       └── github-mcp-setup.md
├── .gitattributes
├── .gitignore
├── .mcp.json             ← 로컬 전용 (gitignore)
├── .mcp.json.example
├── CLAUDE.md
├── HARNESS.md
├── PLAN.md
├── PRD.md
├── README.md
└── REPORT.md
```

GitHub: https://github.com/ltw070/gitshuttle (private)

---

## 다음 작업 (Next)

- [ ] Claude Code 재시작 → SubAgent 등록 확인 (`/agents`)
- [ ] `sprint/0-scaffold` 브랜치 생성
- [ ] SA1 실행 → 문서 정합성 검증
- [ ] SA2 실행 → Sprint 0 구현 (`pyproject.toml`, 패키지 스캐폴딩, `conftest.py`)
- [ ] SA3+SA4 병렬 실행 → 검증 후 `main` merge
