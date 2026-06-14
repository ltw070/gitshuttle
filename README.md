# GitShuttle

망분리(Air-Gapped) 환경에서 Git 리포지토리의 커밋 히스토리와 메타데이터를 완전히 보존하며 이전하는 CLI 도구입니다.

단순 소스 복사와 달리 커밋 메시지, 작성자, 상세 설명, 태그, 브랜치 히스토리를 그대로 유지합니다.

자세한 사용법은 **[MANUAL.md](MANUAL.md)** 를, 단계별 실습 예제는 **[EXAMPLE.md](EXAMPLE.md)** 를 참고하세요.

---

## 요구 사항

| 항목 | 버전 |
|------|------|
| OS | Windows (주 대상) |
| Git | 2.37 이상 |
| Python | 3.10 이상 (`.exe` 사용 시 불필요) |

---

## 설치 및 실행

### 방법 1 — 실행 파일 (권장, Python 불필요)

`gitshuttle.exe` 릴리즈가 등록된 경우 [GitHub Releases](https://github.com/ltw070/gitshuttle/releases)에서 다운로드하여 원하는 경로에 배치합니다.
현재 릴리즈 파일이 없다면 아래 Python 직접 실행 또는 PyInstaller 직접 빌드 방식을 사용하세요.

```
gitshuttle export
gitshuttle import --file shuttle_260508.bundle
gitshuttle config
```

직접 빌드:

```powershell
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File build.ps1
# dist\gitshuttle.exe 생성
```

### 방법 2 — Python 직접 실행

```
git clone https://github.com/ltw070/gitshuttle.git
cd gitshuttle
pip install -r requirements.txt
python -m gitshuttle --help
```

---

## 기본 워크플로우

```
[외부망]  gitshuttle export
            → 커밋 목록에서 전송할 커밋 선택
            → shuttle_YYMMDD.bundle + .sha256 + _manifest.txt 생성

[이동]    USB 또는 망간 전송 시스템으로 내부망 전달

[내부망]  gitshuttle import --file shuttle_260508.bundle
            → SHA-256 체크섬 자동 검증
            → 내부 Git 서버에 히스토리 그대로 반영
```

---

## 명령어

### `export` — 셔틀 패키지 생성

```
gitshuttle export [OPTIONS]

Options:
  --repo PATH                    원본 Git 리포지토리 경로 (기본값: 현재 디렉터리)
  --branch TEXT                  대상 브랜치 (기본값: 현재 브랜치)
  --ui [tui|csv|html|prompt]     커밋 선택 UI 방식 (기본값: 설정 파일 또는 tui)
  --output TEXT                  출력 경로 (기본값: 원본 리포지토리 경로)
  --format [bundle|patchset]     패키지 형식 (기본값: bundle)
```

현재 위치가 원본 리포지토리가 아니어도 `--repo`로 대상 경로를 지정할 수 있습니다.

```
gitshuttle export --repo C:\repos\external-repo --branch main --output C:\transfer
```

기준점 없이 대상 브랜치 위에 cherry-pick처럼 붙이고 싶다면 `patchset` 형식으로 export합니다.

```
gitshuttle export --repo C:\repos\external-repo --branch main --format patchset --output C:\transfer
```

모든 커밋을 선택하고 싶고 TUI 선택 화면을 건너뛰려면 headless 모드를 사용할 수 있습니다.

```powershell
$env:GITSHUTTLE_HEADLESS = "1"
gitshuttle export --repo C:\repos\external-repo --branch main --ui tui --output C:\transfer
Remove-Item Env:\GITSHUTTLE_HEADLESS
```

**커밋 선택 UI 방식:**

| 옵션 | 방식 | 설명 |
|------|------|------|
| `tui` | TUI (기본값) | 터미널 인터랙티브 체크박스·테이블 |
| `csv` | CSV 편집 | `commits.csv` 생성 → Excel에서 `include` 컬럼 Y/N 수정 |
| `html` | Self-contained HTML | 브라우저에서 선택 → `selection.json` 다운로드 |
| `prompt` | InquirerPy | 방향키 + Space 멀티셀렉트 |

이미 타겟 리포지토리에 반영된 커밋은 `[imported]`로 표시됩니다.

### `import` — 셔틀 패키지 반영

```
gitshuttle import --file FILE [OPTIONS]

Options:
  --file TEXT                                .bundle 또는 .patchset 파일 경로 (필수)
  --repo PATH                                대상 Git 리포지토리 경로 (기본값: 현재 디렉터리)
  --on-conflict [skip|force|abort]           충돌 처리 방식 (기본값: skip)
  --author-map FILE                          작성자 매핑 JSON 파일 경로
  --target-branch TEXT                       import 커밋을 담을 브랜치명 (기본값: imported/<소스브랜치>)
  --timestamp [now|original|from=DATETIME]  커밋 타임스탬프 모드 (기본값: now)
  --mode [auto|bundle|replay]                import 방식 (기본값: auto)
```

현재 위치가 대상 리포지토리가 아니어도 `--repo`로 반입 대상 경로를 지정할 수 있습니다.

```
gitshuttle import --file C:\transfer\shuttle_260612.bundle --repo C:\repos\internal-repo
```

**충돌 처리 옵션:**

| 옵션 | 동작 |
|------|------|
| `skip` (기본값) | 이미 존재하는 커밋은 건너뛰고 나머지 계속 진행 |
| `force` | 이미 존재해도 강제 계속 진행. rewrite import에서는 기존 대상 브랜치 ref도 덮어씀 |
| `abort` | 충돌 발견 즉시 전체 작업 중단 |

**브랜치 격리:** 소스의 `main`/`master`는 타겟의 기존 기본 브랜치에 직접 병합되지 않고, 별도 브랜치(`imported/main` 등)로 격리됩니다.
rewrite import 후에는 대상 브랜치로 checkout/reset 되어 작업 폴더의 실제 파일도 import 결과와 맞춰집니다.

**커밋 타임스탬프 옵션:**

| 옵션 | 동작 |
|------|------|
| `now` (기본값) | 모든 커밋 date = import 실행 시각 |
| `original` | 소스 원본 author/committer date 그대로 보존 |
| `from=YYYY-MM-DDTHH:MM:SS` | 최초 커밋 = 지정 시각, 이후 커밋은 원본 상대 간격 유지 |

import 시 SHA-256 체크섬이 자동 검증됩니다. 불일치 시 작업이 중단되며 재export 방법이 안내됩니다.

최근 1~2개처럼 일부 커밋만 export한 bundle은 대상 repo에 그 직전 **원본 부모 커밋 SHA**가 있어야 검증됩니다.
작성자/날짜 rewrite를 적용한 대상 repo는 커밋 SHA가 바뀌므로, 이런 증분 bundle이 `bundle 검증 실패`가 될 수 있습니다.
최신 GitShuttle은 rewrite import 시 원본 bundle refs를 `refs/gitshuttle/original/...` 아래 숨겨 보관해 다음 부분 bundle의 기준점으로 사용합니다.
따라서 이 버전으로 한 번 전체 또는 필요한 기준 범위를 import한 뒤에는 이후 최신 커밋 몇 개만 export/import하는 증분 흐름을 사용할 수 있습니다.
구버전으로 이미 이전한 대상 repo는 한 번 전체 범위를 다시 import해 기준점을 만든 뒤 부분 증분을 이어가세요.

체리픽처럼 변경분만 대상 브랜치 위에 재생하는 방식도 가능하지만, 이는 원본 Git 이력을 그대로 옮기는 bundle 방식과 다릅니다.
커밋 SHA와 merge 구조가 달라질 수 있으므로 GitShuttle의 기본 흐름은 bundle 기반 이력 이전을 유지합니다.

### Replay / Cherry-Pick 방식

`patchset` + `replay`는 원본 기준점 없이 선택 커밋의 변경분을 대상 브랜치 현재 HEAD 위에 새 커밋으로 재생합니다.

```
gitshuttle export --repo C:\repos\source --branch main --format patchset --output C:\transfer
gitshuttle import --repo C:\repos\target --file C:\transfer\shuttle_YYMMDD.patchset --mode replay
```

replay import는 대상 브랜치의 마지막 커밋 메시지와 새로 붙일 첫 커밋 메시지가 같을 때만 경고하고 계속 진행 여부를 확인합니다.
이 방식은 내부 수정이 이미 들어간 브랜치 위에 작업자 책임으로 변경분만 붙일 때 유용하지만, 원본 SHA와 merge topology는 보존하지 않습니다.

이미 같은 변경분이 대상 브랜치에 적용되어 있으면 해당 replay patch는 건너뜁니다.
같은 경로의 파일이 이미 있지만 내용이 달라 `patch failed`, `patch does not apply`, `already exists in index`가 나는 경우에는 충돌로 보고 중단하며, 이미 반영된 커밋 이후만 다시 선택해 patchset을 만드는 것이 안전합니다.

**작성자 매핑 JSON 형식:**

```json
{
  "old@example.com": {
    "name": "ltw070",
    "email": "ltw070@naver.com"
  }
}
```

매핑 키는 `"Name <email>"`이 아니라 이메일 주소만 사용합니다.

### `config` — 설정 마법사

```
gitshuttle config
```

`gitshuttle.toml`의 기본값을 대화형으로 변경합니다.

---

## 설정 파일

작업 디렉터리 또는 홈 디렉터리에 `gitshuttle.toml`을 생성합니다.

```toml
[export]
ui = "tui"   # tui | csv | html | prompt

[import]
timestamp = "now"   # now | original | from=2024-01-01T09:00:00
author_map = "C:\\transfer\\author_map.json"
```

CLI 옵션은 설정 파일보다 항상 우선합니다.

---

## 생성 파일

| 파일 | 설명 |
|------|------|
| `shuttle_YYMMDD.bundle` | Git bundle 패키지 (히스토리 보존) |
| `shuttle_YYMMDD.sha256` | SHA-256 체크섬 (무결성 검증용) |
| `shuttle_YYMMDD_manifest.txt` | 포함된 커밋 목록 요약 (반출입 심사용) |

**3개 파일을 항상 함께 이동하세요.**

---

## 대용량 bundle 분할 압축

USB 용량 제한 시 bundle을 여러 파트로 분할할 수 있습니다.

```python
from gitshuttle.bundle import split_bundle, merge_bundles

# 50MB 단위 분할
parts = split_bundle("shuttle_260508.bundle", chunk_bytes=50 * 1024 * 1024)
# → shuttle_260508.bundle.part000, .part001, ...

# 내부망에서 재조립
merge_bundles(parts, "shuttle_260508_merged.bundle")
```

---

## `sync` — GitHub 간 직접 동기화 (Phase 2)

네트워크가 연결된 환경에서 파일 없이 두 GitHub repo를 직접 동기화합니다.

현재 `gitshuttle sync` CLI는 안내 메시지만 출력합니다. 실제 동기화는 Python API `run_sync()`로 사용할 수 있습니다.

**연결 설정 (`gitshuttle.toml`):**

```toml
[sync.source]
url  = "https://github.com/org1/repo"
auth = "token"

[sync.target]
url  = "https://github.com/org2/repo"
auth = "token"
```

**토큰은 환경변수로 전달합니다 (파일에 직접 저장 금지):**

```
set GS_SOURCE_TOKEN=ghp_...
set GS_TARGET_TOKEN=ghp_...
```

```python
import os
from gitshuttle.sync_ import run_sync

result = run_sync(
    source_url="https://github.com/org1/repo",
    target_url="https://github.com/org2/repo",
    source_token=os.environ["GS_SOURCE_TOKEN"],
    target_token=os.environ["GS_TARGET_TOKEN"],
)
print(result)
```

**SSH 방식:**

```toml
[sync.source]
url     = "git@github.com:org1/repo.git"
auth    = "ssh"
ssh_key = "C:\\Users\\user\\.ssh\\id_rsa_source"
```

---

## 개발 워크플로우 (기여자용)

모든 구현은 TDD Harness를 통해 진행합니다. 자세한 내용은 [`HARNESS.md`](HARNESS.md) 참고.

```
SubAgent1 (문서 정합성 검증)
  → SubAgent2 (TDD 구현)
    → SubAgent3 (테스트 검증) + SubAgent4 (규약 검증)  ← 병렬
```

SubAgent 정의 파일: `.claude/agents/`
