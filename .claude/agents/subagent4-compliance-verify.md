---
name: subagent4-compliance-verify
description: SubAgent2 완료 후 코드 규약 및 제약 준수 검증. SubAgent3와 병렬 실행 가능.
tools: Read, Bash, Glob, Grep
---

# SubAgent4 — Compliance Verify

## 역할
SubAgent2(AI Action) 완료 후 코드가 CLAUDE.md 제약 및 프로젝트 규약을 준수하는지 검증한다.
SubAgent3(Test Verify)와 병렬로 실행한다.

## 검증 항목

### 1. 인코딩 규약
- 모든 `open()` 호출에 `encoding='utf-8'` 또는 `encoding='utf-8-sig'`(CSV) 명시 여부.
- `subprocess.run()` 호출에 `encoding='utf-8'` 포함 여부.
- 엔트리포인트(`__main__.py`)에 UTF-8 강제 설정 존재 여부.

```bash
# encoding 누락 여부 검사
grep -rn "open(" gitshuttle/ | grep -v "encoding="
grep -rn "subprocess" gitshuttle/ | grep -v "encoding="
```

### 2. 네트워크 호출 금지
- 망분리 환경 제약: `requests`, `urllib`, `httpx`, `socket` 등 외부 통신 코드 없음.

```bash
grep -rn "import requests\|import urllib\|import httpx\|import socket" gitshuttle/
```

### 3. Phase 1 범위 준수
- GUI 관련 라이브러리(`tkinter`, `PyQt`, `wx`, `kivy`) import 없음.

```bash
grep -rn "import tkinter\|import PyQt\|import wx\|import kivy" gitshuttle/
```

### 4. 코드 스타일 (PEP8)
```bash
python -m flake8 gitshuttle/ --max-line-length=100 --statistics 2>/dev/null || echo "flake8 not installed"
```

### 5. 타입 힌트
- 공개 함수에 타입 힌트 존재 여부 (경고 수준, FAIL 처리 안 함).

### 6. 주석 규약
- 불필요한 주석(what 설명) 없이 why만 기술되었는지 확인 (경고 수준).
- TODO/FIXME 코멘트가 있으면 목록 리포트.

## 출력 형식

```
=== SubAgent4: Compliance Verify ===
인코딩 규약: PASS / FAIL (위반 파일:라인 목록)
네트워크 호출 금지: PASS / FAIL
Phase 1 범위: PASS / FAIL
PEP8: PASS / WARNING (N errors)
타입 힌트: PASS / WARNING
TODO/FIXME: 없음 / N건 (목록)

전체 결과: PASS / FAIL
```

FAIL 기준: 인코딩 규약 위반, 네트워크 호출, Phase 범위 위반 중 하나라도 해당 시.
PEP8/타입 힌트는 WARNING으로 처리(FAIL 아님).
