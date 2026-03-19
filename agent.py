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
    """LLM configuration from .env.agent.secret."""

    model_config = SettingsConfigDict(
        env_file=".env.agent.secret",
        env_file_encoding="utf-8",
    )

    llm_api_key: str
    llm_api_base: str
    llm_model: str


# Tool definitions for the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Path must be relative to project root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file from project root (e.g., 'wiki/git.md')"
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
            "description": "List files and directories in a given path. Path must be relative to project root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the directory from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# System prompt for the documentation agent
SYSTEM_PROMPT = """You are a documentation assistant that helps users find information in the project wiki.

You have access to two tools:
1. `list_files` - List files and directories in a given path
2. `read_file` - Read the contents of a file

To answer questions:
1. First use `list_files` to explore the wiki directory structure
2. Then use `read_file` to read relevant files
3. Find the answer and include a source reference (file path and section if applicable)
4. When you have the answer, respond with the final message containing the answer

Always include a source reference in your answer, like: "Source: wiki/git-workflow.md#resolving-merge-conflicts"

Limit your tool calls to what's necessary. Once you find the answer, stop calling tools and provide the response.
"""

MAX_TOOL_CALLS = 10


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.resolve()


def is_safe_path(path: str) -> bool:
    """Check if path is safe (no directory traversal)."""
    # Block path traversal attempts
    if ".." in path or path.startswith("/"):
        return False

    project_root = get_project_root()
    try:
        # Resolve the full path
        resolved = (project_root / path).resolve()
        # Ensure it's within project root
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


def execute_tool(tool_name: str, args: dict[str, Any]) -> str:
    """Execute a tool and return the result."""
    if tool_name == "read_file":
        return read_file_tool(args.get("path", ""))
    elif tool_name == "list_files":
        return list_files_tool(args.get("path", ""))
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
    # Look for source pattern like "Source: wiki/file.md" or "wiki/file.md#section"

    # Pattern 1: "Source: path" or "source: path"
    match = re.search(r"[Ss]ource:\s*(\S+)", answer)
    if match:
        return match.group(1)

    # Pattern 2: wiki path with optional anchor
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

        # Check if there are tool calls
        tool_calls = message.get("tool_calls", [])

        if not tool_calls:
            # No more tool calls - extract answer
            answer = message.get("content", "")
            source = extract_source_from_answer(answer)

            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_history,
            }

        # Process tool calls
        messages.append(message)

        for tool_call in tool_calls:
            tool_call_id = tool_call["id"]
            function = tool_call["function"]
            tool_name = function["name"]
            tool_args = json.loads(function["arguments"])

            # Execute the tool
            result = execute_tool(tool_name, tool_args)

            # Record in history
            tool_calls_history.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
            })

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call_id,
            })

            tool_call_count += 1

    # Max iterations reached
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
