# AGENTS.md

## Code Style

- **Indentation**: Tabs (1 tab per level, display width 8 spaces)
- **Format before commit**: Run `python3 scripts/format_tabs.py`

## Architecture

Three-layer design:
- `agent/` — LLM wrapper + Agent orchestrator (ReAct loop)
- `tools/` — Tool registry + individual tools (BaseTool subclasses)
- `utils/` — Logger, rate limiter, retry helpers

## Key Conventions

- Message structure: 4 layers (system | summary | skills | conversation)
- Session files: JSON with structured fields (system_prompt, summary, skills, conversation)
- `/load` then `/save`: overwrites the loaded session file
- `compress_context`: truncates conversation, stores summary in summary_layer
