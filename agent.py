#!/usr/bin/env python3
"""
Agent CLI - Call an LLM from code with tool support.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON with 'answer', 'source', and 'tool_calls' fields to stdout.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Configuration from environment and .env files."""

    model_config = SettingsConfigDict(
        env_file=(".env.agent.secret", ".env.docker.secret"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM configuration
    llm_api_key: str = ""
    llm_api_base: str = ""
    llm_model: str = ""

    # Backend API configuration
    lms_api_key: str = ""
    agent_api_base_url: str = "http://localhost:42002"


# Tool definitions for the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Path must be relative to project root. Use for documentation, code, config files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file from project root (e.g., 'wiki/git.md', 'pyproject.toml')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a given path. Use to discover directory structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the directory from project root (e.g., 'wiki', 'backend/src/backend/routers')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Make an HTTP request to the backend API. Use for live data: item counts, scores, status codes, errors, crashes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE, etc.)"
                    },
                    "path": {
                        "type": "string",
                        "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body (for POST/PUT)"
                    },
                    "auth": {
                        "type": "boolean",
                        "description": "Whether to include authentication (default: true). Set to false to test unauthenticated access."
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

# System prompt for the documentation and system agent
SYSTEM_PROMPT = """You are a documentation and system assistant that helps users find information.

You have access to three tools:
1. `list_files` - List files and directories in a given path
2. `read_file` - Read the contents of a file
3. `query_api` - Make HTTP requests to the backend API

## Project Structure:
- Routers are at: backend/app/routers/
- Main app: backend/app/main.py
- Dependencies: pyproject.toml
- Wiki: wiki/*.md

## Tool Selection:
- Use `list_files` to discover structure (max 2 calls total)
- Use `read_file` for documentation, code, config files
- Use `query_api` for live data, status codes, errors
  - Set `auth: false` to test unauthenticated access (e.g., "without auth header")

## Critical Rules:
1. NEVER call list_files more than 2 times
2. ALWAYS include "Source: <file-path>" at the end of answers from files
3. ALWAYS provide a COMPLETE final answer - never say "let me continue"
4. SUMMARIZE in your own words - don't copy file content

## Examples:
- For router questions: read backend/app/routers/__init__.py for module names
- For framework questions: read pyproject.toml
- For wiki questions: find relevant .md file and read it
- For bug questions: query the endpoint to see the error, then read the source code at the error line
- For top-learners bug: try lab-01 which has data that triggers the sorting bug

Respond with the FINAL answer and source.
"""

MAX_TOOL_CALLS = 10


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.resolve()


def is_safe_path(path: str) -> bool:
    """Check if path is safe (no directory traversal)."""
    if ".." in path or path.startswith("/"):
        return False

    project_root = get_project_root()
    try:
        resolved = (project_root / path).resolve()
        return str(resolved).startswith(str(project_root))
    except (ValueError, OSError):
        return False


def read_file_tool(path: str) -> str:
    """Read contents of a file."""
    if not is_safe_path(path):
        return "Error: Access denied - path traversal not allowed"

    project_root = get_project_root()
    file_path = project_root / path

    if not file_path.exists():
        return f"Error: File not found: {path}"

    if not file_path.is_file():
        return f"Error: Not a file: {path}"

    try:
        return file_path.read_text(encoding="utf-8")
    except (PermissionError, UnicodeDecodeError) as e:
        return f"Error: Cannot read file: {e}"


def list_files_tool(path: str) -> str:
    """List files in a directory."""
    if not is_safe_path(path):
        return "Error: Access denied - path traversal not allowed"

    project_root = get_project_root()
    dir_path = project_root / path

    if not dir_path.exists():
        return f"Error: Directory not found: {path}"

    if not dir_path.is_dir():
        return f"Error: Not a directory: {path}"

    try:
        entries = sorted(dir_path.iterdir())
        lines = []
        for entry in entries:
            prefix = "📁 " if entry.is_dir() else "📄 "
            lines.append(f"{prefix}{entry.name}")
        return "\n".join(lines)
    except PermissionError as e:
        return f"Error: Permission denied: {e}"


def query_api_tool(
    method: str,
    path: str,
    body: str | None = None,
    auth: bool = True,
    settings: AgentSettings | None = None,
) -> str:
    """Make HTTP request to backend API with optional authentication."""
    if settings is None:
        settings = AgentSettings()

    api_base = settings.agent_api_base_url.rstrip("/")
    url = f"{api_base}{path}"

    headers = {
        "Content-Type": "application/json",
    }

    # Add authentication if LMS_API_KEY is available and auth is True
    if auth and settings.lms_api_key:
        headers["Authorization"] = f"Bearer {settings.lms_api_key}"

    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                json_body = json.loads(body) if body else None
                response = client.post(url, headers=headers, json=json_body)
            elif method.upper() == "PUT":
                json_body = json.loads(body) if body else None
                response = client.put(url, headers=headers, json=json_body)
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                return f"Error: Unsupported method: {method}"

            result = {
                "status_code": response.status_code,
                "body": response.text,
            }
            return json.dumps(result)

    except httpx.TimeoutException:
        return "Error: API request timed out"
    except httpx.RequestError as e:
        return f"Error: API request failed: {e}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON body: {e}"


def execute_tool(
    tool_name: str,
    args: dict[str, Any],
    settings: AgentSettings | None = None,
) -> str:
    """Execute a tool and return the result."""
    if tool_name == "read_file":
        return read_file_tool(args.get("path", ""))
    elif tool_name == "list_files":
        return list_files_tool(args.get("path", ""))
    elif tool_name == "query_api":
        return query_api_tool(
            args.get("method", "GET"),
            args.get("path", ""),
            args.get("body"),
            args.get("auth", True),
            settings,
        )
    else:
        return f"Error: Unknown tool: {tool_name}"


def call_llm(
    messages: list[dict[str, Any]],
    settings: AgentSettings,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send messages to LLM and return the response."""
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def extract_source_from_answer(answer: str) -> str:
    """Extract source reference from answer text."""
    match = re.search(r"[Ss]ource:\s*(\S+)", answer)
    if match:
        return match.group(1)

    match = re.search(r"(wiki/[\w\-/]+\.md(?:#[\w\-]+)?)", answer)
    if match:
        return match.group(1)

    return ""


def run_agent(question: str, settings: AgentSettings) -> dict[str, Any]:
    """Run the agentic loop and return the result."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_calls_history: list[dict[str, Any]] = []
    tool_call_count = 0

    while tool_call_count < MAX_TOOL_CALLS:
        response = call_llm(messages, settings, tools=TOOLS)
        message = response["choices"][0]["message"]

        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            answer = message.get("content", "")
            source = extract_source_from_answer(answer)

            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_history,
            }

        messages.append(message)

        for tool_call in tool_calls:
            tool_call_id = tool_call["id"]
            function = tool_call["function"]
            tool_name = function["name"]
            tool_args = json.loads(function["arguments"])

            result = execute_tool(tool_name, tool_args, settings)

            tool_calls_history.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
            })

            messages.append({
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call_id,
            })

            tool_call_count += 1

    return {
        "answer": "I was unable to find the answer within the maximum number of tool calls.",
        "source": "",
        "tool_calls": tool_calls_history,
    }


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        return 1

    question = sys.argv[1]

    try:
        settings = AgentSettings()
        result = run_agent(question, settings)
        print(json.dumps(result))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
