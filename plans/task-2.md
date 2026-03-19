# Task 2: The Documentation Agent — Implementation Plan

## Overview
Build an agentic loop that enables the CLI to call tools (`read_file`, `list_files`) to navigate and search the project wiki, then return answers with source references.

---

## Architecture

### Tool Schemas

#### 1. `read_file`
- **Purpose**: Read contents of a file
- **Parameters**: `path` (string) - relative path from project root
- **Returns**: File contents as string, or error message
- **Security**: Block `../` path traversal attempts

#### 2. `list_files`
- **Purpose**: List files in a directory
- **Parameters**: `path` (string) - relative directory path
- **Returns**: Newline-separated listing of entries
- **Security**: Block access outside project directory

### Agentic Loop Flow

```
1. Send user question + tool definitions to LLM
2. Parse LLM response for tool_calls
3. If tool_calls exist:
   a. Execute each tool with provided arguments
   b. Append tool results as "tool" role messages
   c. Send back to LLM for next iteration
   d. Repeat until no more tool calls or max 10 iterations
4. If no tool_calls:
   a. Extract answer and source from LLM response
   b. Output JSON with answer, source, and tool_calls history
   c. Exit
```

### Message Format (OpenAI-compatible)

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": question},
    # ... tool_call messages
    {"role": "assistant", "tool_calls": [...]},
    {"role": "tool", "content": "...", "tool_call_id": "..."},
    # ... iterations
]
```

---

## Implementation Details

### System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover wiki directory structure
2. Use `read_file` to read relevant wiki files
3. Include source reference in the answer (file path + section anchor)
4. Stop calling tools once the answer is found

### Tool Execution

```python
def execute_tool(tool_name: str, args: dict) -> str:
    if tool_name == "read_file":
        return read_file_tool(args["path"])
    elif tool_name == "list_files":
        return list_files_tool(args["path"])
```

### Path Security

```python
def is_safe_path(path: str) -> bool:
    # Block path traversal
    if ".." in path or path.startswith("/"):
        return False
    # Resolve and verify within project root
    resolved = (PROJECT_ROOT / path).resolve()
    return PROJECT_ROOT in resolved.parents or resolved == PROJECT_ROOT
```

### Output Format

```json
{
  "answer": "To resolve merge conflicts, first identify conflicting files...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

---

## File Structure

```
se-toolkit-lab-6/
├── agent.py              # Updated with tools + agentic loop
├── AGENT.md              # Updated documentation
├── plans/
│   ├── task-1.md         # Task 1 plan
│   └── task-2.md         # This implementation plan
├── tests/
│   └── test_agent.py     # Updated with tool-calling tests
└── wiki/                 # Knowledge base for agent
```

---

## Testing Strategy

### Test 1: Merge Conflict Question
- Question: "How do I resolve a merge conflict?"
- Expected: Agent uses `list_files` and `read_file` to find answer in `wiki/git-workflow.md`
- Validate: `tool_calls` array is populated, `source` field references correct file

### Test 2: Wiki Listing Question
- Question: "What documentation is available in the wiki?"
- Expected: Agent uses `list_files` to discover wiki contents
- Validate: `tool_calls` contains `list_files` call, answer lists available docs

---

## Git Workflow

1. Create GitHub issue: `[Task 2] The Documentation Agent`
2. Create branch: `feature/task-2-docs-agent`
3. Commit `plans/task-2.md` first
4. Implement updated `agent.py`, `AGENT.md`, tests
5. Create PR with `Closes #<issue-number>`
6. Request partner approval
7. Merge to main

---

## Acceptance Criteria Checklist

- [ ] `plans/task-2.md` exists (committed before code)
- [ ] `read_file` and `list_files` defined as tool schemas
- [ ] Agentic loop executes tool calls and feeds results back
- [ ] `tool_calls` array populated in output
- [ ] `source` field correctly identifies wiki section
- [ ] Path security prevents directory traversal
- [ ] `AGENT.md` documents the implementation
- [ ] 2 tool-calling regression tests pass
- [ ] Git workflow followed
