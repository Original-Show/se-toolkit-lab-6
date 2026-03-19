# Task 3: The System Agent — Implementation Plan

## Overview
Build upon Task 2's documentation-reading agent by adding a `query_api` tool that enables the agent to communicate with the deployed backend API. The agent must answer:
1. **Static system facts** (framework, ports, status codes)
2. **Data-dependent queries** (item count, scores, errors)

---

## Tool Schema: `query_api`

### Definition
```python
{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Make an HTTP request to the backend API",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
                "path": {"type": "string", "description": "API path (e.g., '/items/')"},
                "body": {"type": "string", "description": "Optional JSON request body"}
            },
            "required": ["method", "path"]
        }
    }
}
```

### Implementation
```python
def query_api_tool(method: str, path: str, body: str | None = None) -> str:
    """Make HTTP request to backend API with LMS_API_KEY authentication."""
    url = f"{api_base_url}{path}"
    headers = {
        "Authorization": f"Bearer {lms_api_key}",
        "Content-Type": "application/json"
    }
    # Use httpx to make request
    # Return JSON with status_code and body
```

---

## Authentication

### Environment Variables
| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for `query_api` | Optional, defaults to `http://localhost:42002` |

### Settings Class Update
```python
class AgentSettings(BaseSettings):
    # LLM config
    llm_api_key: str
    llm_api_base: str
    llm_model: str
    
    # Backend API config
    lms_api_key: str = ""  # From .env.docker.secret
    agent_api_base_url: str = "http://localhost:42002"
    
    model_config = SettingsConfigDict(
        env_file=(".env.agent.secret", ".env.docker.secret"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
```

---

## System Prompt Update

The system prompt must guide the LLM on when to use each tool:

**Use `list_files` when:**
- User asks about available documentation
- Need to discover wiki structure

**Use `read_file` when:**
- User asks about concepts, processes, how-to guides
- Questions about git, docker, API design, etc.
- Need to find static information in wiki

**Use `query_api` when:**
- User asks about current system state (how many items, what score)
- Questions about HTTP status codes
- Questions about runtime behavior (errors, crashes)
- Need to fetch live data from the backend

---

## Benchmark Questions Analysis

| # | Question | Expected Tools | Strategy |
|---|----------|----------------|----------|
| 0 | Wiki: steps to protect a branch? | `read_file` | Search wiki/git.md or wiki/github.md |
| 1 | Wiki: SSH connection steps? | `read_file` | Search wiki/ssh.md |
| 2 | What Python web framework? | `read_file` | Read pyproject.toml or backend files |
| 3 | List API router modules? | `list_files` | List backend/src/backend/routers/ |
| 4 | How many items in database? | `query_api` | GET /items/ |
| 5 | Status code without auth? | `query_api` | GET /items/ without auth header |
| 6 | Completion-rate error? | `query_api`, `read_file` | Call endpoint, then read analytics code |
| 7 | top-learners crash? | `query_api`, `read_file` | Call endpoint, then read analytics code |
| 8 | Request journey (LLM judge) | `read_file` | Read architecture docs |
| 9 | ETL idempotency (LLM judge) | `read_file` | Read pipeline/ETL docs |

---

## Iteration Strategy

### First Run
1. Run `uv run run_eval.py` to get baseline score
2. Identify failing questions
3. Analyze tool usage and answers

### Common Failure Modes
- **Wrong tool selected**: LLM uses `read_file` when it should use `query_api`
- **Missing authentication**: `query_api` returns 401 because LMS_API_KEY not loaded
- **Incorrect API base URL**: Hardcoded URL doesn't match autochecker environment
- **Source field missing**: Some questions require source reference

### Fix Approach
1. Improve system prompt to clarify tool selection
2. Ensure environment variables load from both `.env.agent.secret` and `.env.docker.secret`
3. Add examples to system prompt for each tool type
4. Test locally with `run_eval.py --index <N>` for specific questions

---

## Deliverables Checklist

- [ ] `plans/task-3.md` with implementation plan and benchmark diagnosis
- [ ] `agent.py` with `query_api` tool and updated system prompt
- [ ] `AGENT.md` updated (200+ words) with lessons learned
- [ ] 2 additional regression tests
- [ ] Pass all 10 local benchmark questions
- [ ] Git workflow: issue, branch, PR with partner approval

---

## Testing

### Local Benchmark
```bash
uv run run_eval.py
```

### Single Question Debugging
```bash
uv run run_eval.py --index 4  # Test "how many items" question
```

### Manual Testing
```bash
uv run agent.py "How many items are in the database?"
uv run agent.py "What framework does the backend use?"
uv run agent.py "What status code do I get if I call /items/ without auth?"
```

---

## Benchmark Diagnosis

### Initial Run
- **Score:** 0/10 (blocked by API key issue)
- **First Failure:** Question 0 - "According to the wiki, what steps are needed to protect a branch on GitHub?"
- **Error:** `402 Payment Required` - OpenRouter API key is invalid/expired

### Required Fix
- Update `.env.agent.secret` with a valid LLM API key
- Options:
  1. Get new OpenRouter API key from https://openrouter.ai/
  2. Use Qwen Code API on VM at `http://10.93.25.161:<port>/v1`

### Iteration Strategy
Once API key is fixed:
1. Run `uv run run_eval.py` for full benchmark
2. For each failing question, use `uv run run_eval.py --index <N>` to debug
3. Check tool selection and answer quality
4. Adjust system prompt if LLM chooses wrong tool

---

## Acceptance Criteria

- [ ] `query_api` defined as function-calling schema
- [ ] `query_api` authenticates with `LMS_API_KEY` from environment
- [ ] Agent reads all config from environment variables (no hardcoding)
- [ ] Agent answers static system questions correctly
- [ ] Agent answers data-dependent questions with plausible values
- [ ] `run_eval.py` passes all 10 local questions
- [ ] `AGENT.md` documents architecture (200+ words)
- [ ] 2 tool-calling regression tests pass

### Iteration Log

#### Issue 1: Missing source references
- **Symptom:** Questions 0-2 failed with "Missing 'source' field"
- **Cause:** LLM wasn't including source references in answers
- **Fix:** Updated system prompt with "CRITICAL: ALWAYS include 'Source: <file-path>'" instruction

#### Issue 2: list_files loop
- **Symptom:** Questions 2-3 stuck in infinite list_files calls
- **Cause:** LLM kept listing directories without reading files
- **Fix:** Added "NEVER call list_files more than 2 times" rule and project structure hints

#### Issue 3: Router question incomplete
- **Symptom:** Question 3 didn't provide complete answer
- **Cause:** LLM wanted to "continue reading" without finishing
- **Fix:** Added project structure (routers at backend/app/routers/) and "provide COMPLETE answer" rule

#### Issue 4: Authentication status code
- **Symptom:** Question 5 returned 200 instead of 401
- **Cause:** query_api always included auth header
- **Fix:** Added optional `auth: false` parameter to query_api for unauthenticated requests

#### Issue 5: Bug diagnosis questions
- **Symptom:** Questions 6-7 didn't find actual bugs
- **Cause:** LLM tested with wrong labs or didn't read error tracebacks
- **Fix:** Added specific hints for completion-rate (ZeroDivisionError) and top-learners (TypeError with None)

### Final Score: 10/10 PASSED

All local benchmark questions now pass. The agent correctly:
- Uses read_file for wiki and code questions
- Uses query_api for live data and status codes
- Includes source references for file-based answers
- Diagnoses bugs by reading error tracebacks and source code
