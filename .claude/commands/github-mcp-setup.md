---
description: GitHub MCP 서버를 설정합니다. GitHub Personal Access Token을 입력받아 .mcp.json을 생성합니다.
---

GitHub MCP 서버 설정을 진행합니다.

## 실행 절차

1. AskUserQuestion 툴로 GitHub Personal Access Token을 입력받는다.
   - 질문: "GitHub Personal Access Token을 입력하세요."
   - 토큰은 https://github.com/settings/tokens 에서 발급 (repo 권한 필요)

2. 프로젝트 루트에 `.mcp.json` 파일을 생성한다:

```json
{
  "mcpServers": {
    "github": {
      "command": "C:\\reviewer\\github-mcp-server_Windows_x86_64\\github-mcp-server.exe",
      "args": ["stdio"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<입력받은 토큰>"
      }
    }
  }
}
```

3. `.mcp.json`이 `.gitignore`에 포함되어 있는지 확인한다. 없으면 추가한다.

4. 완료 메시지 출력:
   - `.mcp.json` 생성 완료
   - Claude Code를 재시작하면 GitHub MCP 툴이 활성화된다.
   - `.mcp.json`은 `.gitignore`에 등록되어 토큰이 git에 커밋되지 않는다.
