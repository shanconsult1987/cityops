
---
mode: agent
description: Investigate a CityOps workflow change safely
---

# Investigate a CityOps change

Before editing files:

1. Read `specs.md` and `.github/copilot-instructions.md`.
2. Identify the relevant application functions and tests.
3. Explain the proposed change and likely risks.
4. Identify effects on classification, approval and audit logging.
5. Propose tests for a normal case and a failure case.

When implementing:

- Keep the change small.
- Prefer the Python standard library.
- Never add real dispatch or production credentials.
- Do not bypass approval or safety-review checks.
- Preserve offline unit tests.
- Run `python -m unittest -v` and `python evaluate.py` when possible.

Finish with a summary of changed files, tests run and remaining risks.
Do not claim tests passed unless they were actually executed successfully.
