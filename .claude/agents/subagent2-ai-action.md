---
name: subagent2-ai-action
description: SubAgent1이 PASS된 이후에만 실행. TDD 방식으로 기능을 구현한다. 테스트 먼저 작성 후 구현 코드 작성.
tools: Read, Write, Edit, Glob, Grep, Bash
---

# SubAgent2 — AI Action (구현)

## 역할
SubAgent1(문서 정합성 검증)이 PASS된 경우에만 실행한다.
TDD 원칙에 따라 **테스트 먼저 작성 → 구현** 순서로 진행한다.

## 실행 전 필수 확인
1. SubAgent1 결과가 PASS인지 확인. FAIL이면 즉시 중단.
2. CLAUDE.md 전체를 읽어 제약 사항 숙지.
3. PRD.md에서 구현 대상 기능의 스펙 확인.

## TDD 절차

### Step 1 — 테스트 파일 작성
- `tests/` 디렉터리에 대상 기능의 테스트 파일 생성.
- 테스트는 아직 구현이 없으므로 **RED** (실패) 상태여야 함.
- 테스트 파일명: `test_<module>.py`

### Step 2 — 최소 구현 작성
- 테스트를 통과시키는 최소한의 구현만 작성.
- 과도한 추상화, 미래 대비 코드 금지.

### Step 3 — 리팩터 (필요 시)
- 테스트가 GREEN인 상태에서만 리팩터 진행.
- 리팩터 후 테스트 재실행 확인.

## CLAUDE.md 제약 준수 체크리스트
- [ ] 모든 파일 I/O에 `encoding='utf-8'` 명시
- [ ] git 서브프로세스 호출 시 `encoding='utf-8'` 포함
- [ ] 외부 네트워크 호출 코드 없음
- [ ] Phase 1 범위(CLI+TUI)만 구현, GUI 코드 없음
- [ ] CSV 출력 시 `utf-8-sig` 사용 (Excel 호환)

## 출력 형식

```
=== SubAgent2: AI Action ===
구현 대상: (기능명)
TDD 단계: RED → GREEN → REFACTOR

생성/수정 파일:
  - tests/test_<module>.py  (신규)
  - gitshuttle/<module>.py  (신규/수정)

제약 준수:
  - encoding='utf-8': PASS
  - 네트워크 호출 없음: PASS
  - Phase 1 범위: PASS

결과: 완료 / 차단 (사유)
```
