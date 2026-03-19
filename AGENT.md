# Agent

A Python CLI tool that calls an LLM with tool support to answer questions using the project wiki.

## Overview

`agent.py` is a command-line interface that:
1. Takes a question as input
2. Uses an agentic loop to call tools (`read_file`, `list_files`)
3. Searches the project wiki for answers
4. Returns a structured JSON response with the answer and source reference

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

### `list_files`
List files and directories in a given path.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Relative directory path from project root (e.g., `wiki`) |

**Returns:** Newline-separated listing with emoji prefixes (📁 for directories, 📄 for files).

**Security:** Blocks access outside project directory.

## LLM Provider

### Current Configuration: OpenRouter
- **Model:** `qwen/qwen3-coder-plus`
- **API Base:** `https://openrouter.ai/api/v1`
- **API Key:** Stored in `.env.agent.secret`

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
uv run agent.py "How do I resolve a merge conflict?"

# Example output
{
  "answer": "To resolve a merge conflict, first identify the conflicting files using 'git status'. Then open each file and look for conflict markers (<<<<<<, ======, >>>>>>). Edit the file to keep the desired changes and remove the markers. Finally, stage the resolved file with 'git add' and continue the merge.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "📄 git.md\n📄 git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git Workflow\n\n## Resolving Merge Conflicts\n..."
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
- `source`: Reference to the wiki file (and section if available)
- `tool_calls`: Array of tool calls made during the agentic loop

## System Prompt Strategy

The system prompt instructs the LLM to:
1. Use `list_files` to discover the wiki directory structure
2. Use `read_file` to read relevant wiki files
3. Include a source reference in the answer (file path + section anchor)
4. Stop calling tools once the answer is found

## Path Security

The agent prevents directory traversal attacks:
- Blocks `..` in paths
- Blocks absolute paths starting with `/`
- Resolves paths and verifies they're within project root

```python
def is_safe_path(path: str) -> bool:
    if ".." in path or path.startswith("/"):
        return False
    resolved = (project_root / path).resolve()
    return str(resolved).startswith(str(project_root))
```

## Error Handling

- All debug/logging output goes to stderr
- Only valid JSON goes to stdout
- API timeout: 60 seconds
- Maximum 10 tool calls per question
- Exit code 0 on success, non-zero on errors

## Testing

```bash
# Run regression tests
uv run pytest tests/test_agent.py -v

# Manual testing
uv run agent.py "What documentation is available in the wiki?"
uv run agent.py "How do I resolve a merge conflict?"
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI program with agentic loop |
| `.env.agent.secret` | LLM configuration (not committed) |
| `.env.agent.example` | Configuration template |
| `AGENT.md` | This documentation |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `tests/test_agent.py` | Regression tests |
| `wiki/` | Knowledge base for the agent |

## Limitations

- Maximum 10 tool calls per question
- Requires valid LLM API key
- Only accesses files within project root
- No caching of file reads (each call reads from disk)
