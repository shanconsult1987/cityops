
# CityOps AI - BPR

A small educational project demonstrating GitHub-centered development of an
AI-assisted municipal service planning workflow.

## Safety notice
This is a simulation. It does not connect to municipal systems or perform
real-world dispatch. The local approval command is not production authentication.

## Requirements
- Python 3.11+
- Git
- GitHub CLI for repository operations
- Optional: OpenAI Developer Platform API key
- Optional: MCP-compatible client

## Install
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configure optional OpenAI access
Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
Never commit `.env`.

Without a key, deterministic classification continues to work.

## Run the application
```powershell
python app.py create "Broken streetlight near the park"
python app.py list
python -m unittest -v
python evaluate.py
```

To approve an eligible planned request, copy its ID from the output:
```powershell
python app.py approve CITY-XXXXXXXX "Workshop Reviewer"
```

The approval command changes local demonstration state only.

## MCP
`mcp_server.py` exposes read-only tools for checking request status and
previewing routing. Configure it in a compatible MCP client.

## GitHub capabilities demonstrated
- Copilot instructions, prompts and agent customization
- Branches, pull requests and code review
- GitHub Actions CI
- CodeQL code scanning
- Dependabot dependency updates
- Dependency review
- Secret scanning and push protection, where supported
- Evaluation and test evidence
- Repository security policy and governance
