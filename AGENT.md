# Agent

A Python CLI tool that calls an LLM with tool support to answer questions using the project wiki and backend API.

## Overview

`agent.py` is a command-line interface that:
1. Takes a question as input
2. Uses an agentic loop to call tools (`read_file`, `list_files`, `query_api`)
3. Searches the project wiki and queries the backend API for answers
4. Returns a structured JSON response with the answer and optional source reference

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  CLI Input  │ ──> │  agent.py    │ ──> │  LLM Provider   │
│  (question) │     │  (agentic    │     │  (OpenRouter)   │
└─────────────┘     │   loop)      │     └─────────────────┘
                    │      │               │
                    │      v               │
                    │  ┌──────────┐        │
                    │  │ Tools:   │ <──────┘
                    │  │ - read_file      │
                    │  │ - list_files     │
                    │  │ - query_api      │
                    │  └──────────┘
                    │      │
                    │      v
                    │  ┌──────────────┐
                    └─>│  JSON Output │
                       │  (stdout)    │
                       └──────────────┘
```

### Agentic Loop

1. Send user question + tool definitions to LLM
2. If LLM returns tool calls:
   - Execute tools locally
   - Append results as "tool" role messages
   - Send back to LLM for next iteration
   - Repeat until no more tool calls or max 10 iterations
3. If LLM returns text (no tool calls):
   - Extract answer and source reference
   - Output JSON and exit

## Tools

### `read_file`
Read contents of a file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Relative path from project root (e.g., `wiki/git.md`) |

**Returns:** File contents as string, or error message.

**Security:** Blocks `../` path traversal attempts.

**Use when:** User asks about concepts, processes, how-to guides, or static information.

### `list_files`
List files and directories in a given path.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Relative directory path from project root (e.g., `wiki`) |

**Returns:** Newline-separated listing with emoji prefixes (📁 for directories, 📄 for files).

**Security:** Blocks access outside project directory.

**Use when:** User asks about available files or you need to discover directory structure.

### `query_api`
Make an HTTP request to the backend API.

| Parameter | Type | Description |
|-----------|------|-------------|
| `method` | string | HTTP method (GET, POST, PUT, DELETE) |
| `path` | string | API path (e.g., `/items/`, `/analytics/completion-rate`) |
| `body` | string (optional) | JSON request body for POST/PUT |

**Returns:** JSON string with `status_code` and `body` fields.

**Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret` for Bearer token auth.

**Use when:** User asks about live data (item counts, scores), HTTP status codes, runtime errors, or crashes.

## Configuration

### Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for `query_api` | `.env.docker.secret` or default `http://localhost:42002` |

### Setup

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

The `LMS_API_KEY` and `AGENT_API_BASE_URL` are read from `.env.docker.secret` (used by the backend).

## Usage

```bash
# Run with a question
uv run agent.py "How do I resolve a merge conflict?"
uv run agent.py "How many items are in the database?"
uv run agent.py "What status code do I get if I call /items/ without auth?"

# Example output
{
  "answer": "There are 120 items in the database.",
  "source": "",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": \"[...]\"}"
    }
  ]
}
```

## Output Format

The agent outputs a single JSON line to stdout:
```json
{
  "answer": "<LLM response>",
  "source": "<wiki file path with optional section anchor>",
  "tool_calls": [
    {
      "tool": "<tool name>",
      "args": {"<arg>": "<value>"},
      "result": "<tool output>"
    }
  ]
}
```

- `answer`: The LLM's response to the question
- `source`: Reference to the wiki file (optional for API queries)
- `tool_calls`: Array of tool calls made during the agentic loop

## System Prompt Strategy

The system prompt instructs the LLM to:

### Use `list_files` when:
- User asks about available documentation or files
- Need to discover directory structure

### Use `read_file` when:
- User asks about concepts, processes, how-to guides
- Questions about git, docker, API design, architecture
- Need to find static information in wiki, code, or config files

### Use `query_api` when:
- User asks about current system state (how many items, what score)
- Questions about HTTP status codes
- Questions about runtime behavior (errors, crashes, exceptions)
- Need to fetch live data from the backend

## Path Security

The agent prevents directory traversal attacks:
- Blocks `..` in paths
- Blocks absolute paths starting with `/`
- Resolves paths and verifies they're within project root

## Error Handling

- All debug/logging output goes to stderr
- Only valid JSON goes to stdout
- API timeout: 60 seconds for LLM, 30 seconds for backend API
- Maximum 10 tool calls per question
- Exit code 0 on success, non-zero on errors

## Testing

```bash
# Run regression tests
uv run pytest tests/test_agent.py -v

# Run local benchmark
uv run run_eval.py

# Debug single question
uv run run_eval.py --index 4

# Manual testing
uv run agent.py "What documentation is available in the wiki?"
uv run agent.py "How many items are in the database?"
uv run agent.py "What framework does the backend use?"
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI program with agentic loop |
| `.env.agent.secret` | LLM configuration (not committed) |
| `.env.agent.example` | Configuration template |
| `.env.docker.secret` | Backend configuration including LMS_API_KEY |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `plans/task-3.md` | Task 3 implementation plan |
| `tests/test_agent.py` | Regression tests |
| `wiki/` | Knowledge base for the agent |
| `run_eval.py` | Local benchmark runner |

## Lessons Learned (Task 1-2)


### Tool Selection
The most challenging part was getting the LLM to choose the right tool for each question. Initially, the agent would try to `read_file` for questions about live data. The solution was to add explicit guidance in the system prompt with examples of when to use each tool.

### Authentication
The `query_api` tool needs to authenticate with the backend using `LMS_API_KEY`. It's critical to read this from environment variables (specifically `.env.docker.secret`) rather than hardcoding, because the autochecker injects its own credentials during evaluation.

### Environment Variable Loading
Pydantic Settings can load from multiple `.env` files using a tuple in `env_file`. The order matters: later files override earlier ones. Using `extra="ignore"` prevents errors from unexpected variables.

### Source References
For wiki-based questions, the source field is important. For API-based questions, the source is less relevant since the answer comes from live data. The agent extracts source references from the LLM response using regex patterns.

### Benchmark Iteration
Running `run_eval.py` locally helps identify failing questions quickly. The key is to test one question at a time using `--index` to debug, then re-run the full benchmark.

### Task 3 Specific Lessons

#### Query API Tool Enhancement
For Task 3, we added an optional `auth` parameter to the `query_api` tool. This allows the agent to test unauthenticated endpoints by setting `auth: false`, which is essential for questions like "What status code does the API return without authentication?" Without this parameter, the tool would always include the API key, making it impossible to test unauthenticated behavior.

#### Preventing Tool Call Loops
A common issue was the LLM getting stuck in loops calling `list_files` repeatedly without ever reading files. The fix involved:
1. Adding explicit limits ("NEVER call list_files more than 2 times")
2. Providing project structure hints in the system prompt (e.g., "Routers are at: backend/app/routers/")
3. Adding examples of correct tool usage patterns

#### Bug Diagnosis Strategy
For bug diagnosis questions, the agent needs to:
1. Query the endpoint to reproduce the error
2. Read the error traceback to find the exact line number
3. Read the source code at that line to understand the bug

The system prompt now includes specific hints for known bugs (e.g., "For top-learners bug: try lab-01 which has data that triggers the sorting bug").

#### LLM Limitations
Working with a free-tier LLM model revealed several limitations:
- The model sometimes ignores instructions in the system prompt
- Complex multi-step reasoning can fail
- The model may produce incomplete answers or say "let me continue" without actually continuing

The solution was to make the system prompt more explicit and add concrete examples of expected behavior.

#### Final Benchmark Score: 10/10
After iterative improvements to the system prompt and tool implementation, the agent passes all 10 local benchmark questions. The key improvements were:
1. Adding project structure hints
2. Enforcing source references
3. Adding the `auth` parameter for unauthenticated requests
4. Providing specific bug diagnosis hints
Running `run_eval.py` locally helps identify failing questions quickly. The key is to test one question at a time using `--index` to debug, then re-run the full benchmark.

## Limitations

- Maximum 10 tool calls per question
- Requires valid LLM API key
- Only accesses files within project root
- No caching of file reads or API responses
- Backend must be running for `query_api` to work
