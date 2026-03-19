# Task 1: Call an LLM from Code — Implementation Plan

## Overview
Build a Python CLI (`agent.py`) that takes a question as input, sends it to an LLM via an OpenAI-compatible API, and returns a structured JSON response.

---

## LLM Provider & Model

### Selected Provider: OpenRouter
- **Reason**: Free tier available, no need to manage local Qwen Code API for this task
- **Model**: `qwen/qwen3-coder-plus` (or `meta-llama/llama-3.3-70b-instruct:free` as fallback)
- **API Base**: `https://openrouter.ai/api/v1`
- **API Key**: Stored in `.env.agent.secret` (already configured)

### Alternative (if needed)
- Qwen Code API running on VM at `http://10.93.25.161:<port>/v1`

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  CLI Input  │ ──> │  agent.py    │ ──> │  OpenRouter API │
│  (question) │     │  (OpenAI SDK)│     │  (LLM)          │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           v
                    ┌──────────────┐
                    │  JSON Output │
                    │  (stdout)    │
                    └──────────────┘
```

### Components
1. **Environment Loading**: Use `pydantic-settings` to load `.env.agent.secret`
2. **OpenAI Client**: Use `openai` package (already in dependencies via httpx)
3. **CLI Interface**: Parse command-line argument with `sys.argv`
4. **Response Processing**: Extract answer, format JSON output
5. **Error Handling**: Log errors to stderr, exit with code 0 on success

---

## Implementation Details

### Dependencies
- Already available: `pydantic-settings`, `httpx` (for API calls)
- Will use: Standard library `sys`, `json`, `os`

### Output Format
```json
{"answer": "<LLM response>", "tool_calls": []}
```

### Error Handling
- All debug/logging output → stderr
- Only valid JSON → stdout
- Timeout: 60 seconds for API call
- Exit code 0 on success, non-zero on errors

---

## File Structure
```
se-toolkit-lab-6/
├── agent.py              # Main CLI program
├── .env.agent.secret     # LLM configuration (already exists)
├── AGENT.md              # Documentation
├── plans/
│   └── task-1.md         # This implementation plan
└── tests/
    └── test_agent.py     # Regression test
```

---

## Git Workflow

1. Create GitHub issue: `[Task 1] Call an LLM from Code`
2. Create branch: `feature/task-1-llm-cli`
3. Commit `plans/task-1.md` first
4. Implement `agent.py`, `AGENT.md`, tests
5. Create PR with `Closes #<issue-number>`
6. Request partner approval
7. Merge to main

---

## Testing Strategy

### Regression Test
- Run `agent.py` as subprocess with test question
- Validate JSON output has required fields: `answer`, `tool_calls`
- Verify `tool_calls` is empty array
- Check exit code is 0

### Manual Testing
```bash
uv run agent.py "What does REST stand for?"
uv run agent.py "Explain dependency injection in 1 sentence"
```

---

## Acceptance Criteria Checklist

- [ ] `plans/task-1.md` exists with implementation plan
- [ ] `agent.py` exists in project root
- [ ] `uv run agent.py "..."` outputs valid JSON with required fields
- [ ] API key stored in `.env.agent.secret` (not hardcoded)
- [ ] `AGENT.md` documents the solution architecture
- [ ] 1 regression test exists and passes
- [ ] Git workflow followed
