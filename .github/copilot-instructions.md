# CityOps AI - GitHub Copilot Instructions

## Project purpose
Build a small municipal service request planning and review assistant.
This is a demonstration only. Never connect it to real dispatch systems.

## Technology constraints
- Use Python 3.11 or later.
- Prefer the Python standard library.
- Use the OpenAI Python SDK only for the optional OpenAI integration.
- Use the MCP Python SDK only for the MCP demonstration.
- Do not introduce a web framework, database, Docker, or agent framework.
- Keep the application runnable from PowerShell.

## Engineering rules
- Keep application logic readable and testable.
- Validate all user input.
- Unknown classifications must go to manual review.
- Never treat an AI suggestion as authorization to dispatch.
- Record important state changes in the audit log.
- Keep secrets out of source code and Git history.
- Tests must run without an OpenAI API key.
- Use unittest unless there is a strong reason not to.
- Explain why a change is needed before making broad edits.