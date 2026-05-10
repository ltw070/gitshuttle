# PR Review Points

---

## PR 제목

```
feat(sprint-4b): Import Rewrite — 작성자 매핑 · 브랜치 격리 · 타임스탬프 재작성
```

---

## PR Description

### 개요

서로 다른 리포지토리 간 커밋 이전 시 발생하는 세 가지 불일치 문제를 `import` 시점에 해결합니다.

| 문제 | 해결 |
|------|------|
| 소스 작성자 정보가 타겟 조직 계정과 다름 | `--author-map` 옵션으로 이메일 기반 작성자 치환 |
| 소스 `main`/`master`가 타겟 기본 브랜치를 덮어쓸 위험 | 기본값 `imported/<소스브랜치>` 로 신규 브랜치 격리 |
| import 시각이 원본 개발 이력과 달라 감사 추적 혼란 | `--timestamp` 3모드로 반영 시각 선택 |

---

### 변경 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `gitshuttle/rewrite.py` | 신규 | fast-export 스트림 파싱·치환 파이프라인 |
| `gitshuttle/import_.py` | 확장 | `--author-map`, `--target-branch`, `--timestamp` 옵션 추가 |
| `gitshuttle/config.py` | 확장 | `[import.author_map]`, `[import.timestamp]` toml 섹션 읽기 |
| `gitshuttle/cli.py` | 확장 | CLI 옵션 등록 및 우선순위 처리 |
| `tests/test_rewrite.py` | 신규 | 28개 단위 테스트 |
| `PRD.md` | 업데이트 | 섹션 3.6 Import-time Rewrite 스펙 추가 |
| `PLAN.md` | 업데이트 | Sprint 4b 삽입 |
| `README.md` | 업데이트 | import 옵션 테이블 확장 |
| `MANUAL.md` | 업데이트 | 섹션 7-1 신규 (브랜치 격리·작성자 매핑·타임스탬프 상세) |
| `EXAMPLE.md` | 업데이트 | 예제 3 — Import Rewrite 실전 시나리오 |

---

### 핵심 구현 상세

#### 1. `rewrite.py` — fast-export/fast-import 파이프라인

```
git fast-export <branch>
  │
  ├── rewrite_authors()     : author/committer 이름+이메일 치환
  ├── rewrite_branch_ref()  : refs/heads/* → refs/heads/<target>
  └── rewrite_timestamps()  : mode 에 따라 타임스탬프 재작성
  │
git fast-import
```

- 스트림을 **텍스트 라인 단위** 정규식 치환 — blob 바이너리는 그대로 통과
- `git fast-import` subprocess는 **바이너리 모드** (`input=bytes`) 로 호출
  → Windows CRLF 변환 방지 (`blob\r\n` → `blob?` 오류 방지)

#### 2. `--timestamp` 3모드

| 모드 | 동작 |
|------|------|
| `now` (기본) | 모든 커밋 committer/author date = import 실행 UTC 시각 |
| `original` | 소스 원본 date 그대로 통과 |
| `from=YYYY-MM-DDTHH:MM:SS` | 최초 커밋 = 지정 UTC 시각, 이후 커밋은 원본 상대 간격 유지 |

> `from=` 값은 **UTC** 기준입니다. 10:23 AM KST → `from=2026-05-09T01:23:00`

#### 3. `rewrite_needed` 조건

```python
rewrite_needed = (
    author_map_path is not None   # 작성자 매핑 파일 지정 시
    or target_branch is not None  # 브랜치명 지정 시
    or timestamp_mode != "now"    # original 또는 from= 사용 시
)
```

세 옵션 모두 기본값이면 기존 unbundle 경로를 유지 → **기존 동작 호환성 보장**

---

### 리뷰 요청 포인트

#### 🔴 중점 검토

1. **`rewrite.py:_IDENTITY_RE` 정규식** (`rewrite.py:20~30`)
   - `author/committer` 라인의 이름·이메일·타임스탬프를 한번에 캡처
   - 이름에 특수문자(`<`, `>`, 한글 등)가 포함된 경우 매칭 실패 여부 검토 필요

2. **`rewrite_timestamps` — `from=` 모드 offset 계산** (`rewrite.py:183~210`)
   - 스트림 내 최솟값 Unix timestamp를 기준점으로 삼아 모든 timestamp에 동일 offset 적용
   - author date와 committer date가 다른 커밋에서 두 값 모두 offset 적용되는지 확인

3. **`_rewrite_and_import` 바이너리 모드 처리** (`import_.py:490~560`)
   - `git fast-export` 출력: `encoding='utf-8', errors='surrogateescape'`
   - `git fast-import` 입력: `input=stream.encode('utf-8')` (bytes, encoding 파라미터 없음)
   - 한글 커밋 메시지·파일명 포함 시 round-trip 무결성 확인 필요

#### 🟡 일반 검토

4. **`author_map.json` 키 형식** — 이메일 주소만 키로 사용 (`"ltw070@naver.com"`)
   - `"Name <email>"` 형식 키는 **동작하지 않음** — 문서에만 명시, 코드 레벨 validation 미구현
   - 잘못된 키 형식 입력 시 경고 없이 미매핑으로 처리됨 → 추후 개선 여지

5. **`_detect_source_branch`** (`import_.py:~390`)
   - bundle에 named ref가 없으면 fallback으로 `main` 반환
   - bundle 생성 시 임시 브랜치 없이 commit hash만 지정한 경우 `imported/main`이 기본값으로 사용됨

6. **toml `[import.author_map]` 섹션 우선순위** (`config.py:~260`)
   - CLI `--author-map` 파일 경로 > toml inline 매핑
   - 두 설정이 동시에 존재할 때 toml inline이 무시됨 — 의도된 동작이나 사용자에게 명확히 안내 필요

#### 🟢 확인 완료

- 전체 테스트 **134/134 PASS** (test_rewrite.py 28개 포함)
- SA4 규약 검증 PASS: 인코딩, 네트워크 호출 없음, Phase 1 범위
- 기존 import 테스트(test_import.py, test_e2e.py) 회귀 없음

---

### 테스트 방법

```bash
# 단위 테스트
python -m pytest tests/test_rewrite.py -v

# 전체 회귀
python -m pytest tests/ -v --tb=short

# 실전 검증 (EXAMPLE.md 예제 3 참고)
gitshuttle import \
  --file first10.bundle \
  --author-map author_map.json \
  --target-branch feat/my-branch \
  --timestamp from=2024-01-01T01:00:00
```

---

### Breaking Changes

없음. 기존 `gitshuttle import --file <bundle>` 호출은 변경 없이 동작합니다.

---

### 관련 문서

- PRD 섹션 3.6 — Import-time Rewrite 스펙
- PLAN.md Sprint 4b — 구현 계획 및 수락 기준
- EXAMPLE.md 예제 3 — 실전 시나리오 (gitshuttle_copyTest 이전)
- MANUAL.md 섹션 7-1 — 사용자 가이드
