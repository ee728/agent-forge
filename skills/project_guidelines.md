---
name: project-guidelines
description: Project-specific coding and testing conventions for AgentForge. Use when making any code changes to ensure consistent style, complete test coverage, and proper commit hygiene.
---

# AgentForge Project Guidelines

## Coding Conventions

### Indentation
- Tabs only (1 tab = 1 indentation level)
- Display width 8 spaces
- Run `python3 scripts/format_tabs.py` before every commit

### Architecture (3-layer)
- `agent/` — LLM wrapper + Agent orchestrator (ReAct loop)
- `tools/` — Tool registry + individual tools (BaseTool subclasses)
- `utils/` — Shared utilities (Logger, sanitize, rate limiter, etc.)

Dependency direction: `agent/` ← depends on → `tools/` and `utils/`. Tools never import from `agent/`.

### Message Structure
4 layers assembled at API call time via `Agent._messages`:
1. `system_layer` — system prompt
2. `summary_layer` — compressed context summary (empty if unused)
3. `skills_layer` — runtime-loaded skills
4. `conversation` — user/assistant/tool messages

### Session Management
- Fresh session → first `/save` creates new file
- `/load <file>` → subsequent `/save` overwrites that same file
- `/exit` auto-saves (same overwrite rule)
- Session file format: JSON with `system_prompt`, `summary`, `skills`, `conversation` fields

## Test Mandate

**Every code change must include corresponding test coverage.**

### Test Framework
- Test files live in `tests/` directory tree
- Each `*_test.py` exports a `suite()` function returning `bool`
- Run all tests: `python3 tests/run.py`
- Test infrastructure in `tests/check.py`: `TestResult`, `check()`, `TempHistory`

### Coverage Rules
| Change Type | Required |
|---|---|
| New feature | Add test(s) in the relevant `tests/` subdirectory |
| Bug fix | Add test that reproduces the bug, then fix |
| Refactor | Ensure existing tests still pass |
| New tool | Add `tests/tools/<name>_test.py` |

### Test Patterns
- Agent tests use `MockLLM` (from `tests/agent/*_test.py`)
- Tool tests exercise both success and error paths
- Session tests use `TempHistory` context manager to isolate filesystem state
- Add tests at the right layer: utility tests go in `tests/utils/`, agent tests in `tests/agent/`, tool tests in `tests/tools/`

## Commit Hygiene

### Format before commit
```
python3 scripts/format_tabs.py
```

### Run tests before commit
```
python3 tests/run.py
```

### Commit message must include test results
Every commit log entry MUST contain a line like:
```
Tests: 76 passed, 0 failed (4 suites)
```
This documents the verified state at each change.

### Commit message style
- Prefix: `feat:` for new features, `fix:` for bug fixes, `refactor:` for code restructuring
- Body: brief summary of what changed and why
- Footer: test result line
