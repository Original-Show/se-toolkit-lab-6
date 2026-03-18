# Agent

A Python CLI tool that calls an LLM to answer questions.

## Overview

`agent.py` is a command-line interface that:
1. Takes a question as input
2. Sends it to an LLM via an OpenAI-compatible API
3. Returns a structured JSON response with the answer

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  CLI Input  │ ──> │  agent.py    │ ──> │  LLM Provider   │
│  (question) │     │  (httpx)     │     │  (OpenRouter)   │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           v
                    ┌──────────────┐
                    │  JSON Output │
                    │  (stdout)    │
                    └──────────────┘
```

## LLM Provider

### Current Configuration: OpenRouter
- **Model**: `qwen/qwen3-coder-plus`
- **API Base**: `https://openrouter.ai/api/v1`
- **API Key**: Stored in `.env.agent.secret`

### Alternative: Qwen Code API
For local/VM deployment, configure in `.env.agent.secret`:
```
LLM_API_BASE=http://10.93.25.161:<port>/v1
LLM_MODEL=qwen3-coder-plus
```

## Configuration

Copy and configure `.env.agent.secret` from `.env.agent.example`:

```bash
cp .env.agent.example .env.agent.secret
nano .env.agent.secret
```

Required variables:
```
LLM_API_KEY=your-api-key-here
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=qwen/qwen3-coder-plus
```

## Usage

```bash
# Run with a question
uv run agent.py "What does REST stand for?"

# Example output
{"answer": "Representational State Transfer.", "tool_calls": []}
```

## Output Format

The agent outputs a single JSON line to stdout:
```json
{
  "answer": "<LLM response>",
  "tool_calls": []
}
```

- `answer`: The LLM's response to the question
- `tool_calls`: Empty array (populated in Task 2)

## Error Handling

- All debug/logging output goes to stderr
- Only valid JSON goes to stdout
- API timeout: 60 seconds
- Exit code 0 on success, non-zero on errors

## Testing

```bash
# Run regression tests
uv run pytest tests/test_agent.py -v

# Manual testing
uv run agent.py "Explain dependency injection in 1 sentence"
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI program |
| `.env.agent.secret` | LLM configuration (not committed) |
| `.env.agent.example` | Configuration template |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Implementation plan |
| `tests/test_agent.py` | Regression tests |
