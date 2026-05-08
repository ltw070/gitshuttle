# GitShuttle TDD Harness

## 워크플로우

```
[Task 입력]
      │
      ▼
┌─────────────────────────────┐
│  SubAgent1: 문서 정합성 검증  │  PRD ↔ README ↔ CLAUDE.md 일관성 확인
└─────────────────────────────┘
      │
   PASS? ──── FAIL ──→ 문서 수정 후 재실행
      │
      ▼
┌─────────────────────────────┐
│  SubAgent2: AI Action        │  TDD: 테스트 작성 → 구현 → 리팩터
└─────────────────────────────┘
      │
      ├──────────────────────┐
      ▼                      ▼
┌────────────┐      ┌─────────────────────┐
│ SubAgent3  │      │     SubAgent4        │  ← 병렬 실행
│ Test Verify│      │ Compliance Verify    │
└────────────┘      └─────────────────────┘
      │                      │
      └──────────┬───────────┘
                 ▼
           둘 다 PASS?
                 │
           ┌─────┴─────┐
          PASS         FAIL
           │             │
           ▼             ▼
        완료        SubAgent2 재실행
                   (문제 수정 후)
```

---

## 각 SubAgent 역할 요약

| Agent | 역할 | 실행 시점 | 병렬 가능 |
|-------|------|-----------|-----------|
| SubAgent1 | 문서 정합성 검증 | 구현 전 | 단독 |
| SubAgent2 | AI Action (TDD 구현) | SA1 PASS 후 | 단독 |
| SubAgent3 | Test Verify | SA2 완료 후 | SA4와 병렬 |
| SubAgent4 | Compliance Verify | SA2 완료 후 | SA3와 병렬 |

---

## 오케스트레이터 실행 방법

메인 Claude Code 세션에서 아래 순서로 SubAgent를 호출한다.

### 1단계 — SubAgent1 실행 (순차)
```
Agent(subagent_type="subagent1-doc-verify", prompt="PRD.md, README.md, CLAUDE.md 정합성 검증 실행")
```
→ FAIL 시 중단, 문서 수정 후 재실행.

### 2단계 — SubAgent2 실행 (순차)
```
Agent(subagent_type="subagent2-ai-action", prompt="[구현 대상 기능 설명]")
```

### 3단계 — SubAgent3 + SubAgent4 병렬 실행
단일 메시지에 두 Agent 호출을 동시에 작성:
```
Agent(subagent_type="subagent3-test-verify", ...)
Agent(subagent_type="subagent4-compliance-verify", ...)
```

### 4단계 — 결과 수집
- SA3, SA4 모두 PASS → 완료, 커밋.
- 하나라도 FAIL → SA2 재실행(수정) → SA3+SA4 재검증.

---

## FAIL 처리 규칙

| FAIL 주체 | 조치 |
|-----------|------|
| SubAgent1 | 문서 수정 후 SA1 재실행. SA2 진행 금지. |
| SubAgent2 | 구현 수정 후 SA2 재실행. |
| SubAgent3 | 테스트/구현 수정 후 SA2 → SA3+SA4 재실행. |
| SubAgent4 | 규약 위반 수정 후 SA2 → SA3+SA4 재실행. |

---

## SubAgent 정의 파일 위치

```
.claude/agents/
├── subagent1-doc-verify.md
├── subagent2-ai-action.md
├── subagent3-test-verify.md
└── subagent4-compliance-verify.md
```
