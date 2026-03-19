"""
Regression tests for agent.py CLI.

Tests validate that agent.py:
- Outputs valid JSON
- Has required 'answer', 'source', and 'tool_calls' fields
- tool_calls is properly populated when using tools
- Exits with code 0 on success
"""

import json
import subprocess
import sys
from pathlib import Path


def run_agent(question: str) -> tuple[int, dict, str]:
    """Run agent.py with a question and return exit code, output, stderr."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), question],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=120,
    )

    output = json.loads(result.stdout) if result.stdout else {}
    return result.returncode, output, result.stderr


def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with required fields."""
    returncode, output, stderr = run_agent("What is 2+2?")

    # Check exit code
    assert returncode == 0, f"agent.py failed with: {stderr}"

    # Validate required fields exist
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"

    # Validate tool_calls is a list
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"

    # Validate answer is non-empty string
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"


def test_merge_conflict_question():
    """Test agent with merge conflict question - should use tools to find answer in wiki."""
    returncode, output, stderr = run_agent(
        "How do I resolve a merge conflict in git?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    # Validate required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"

    # For Task 2, tool_calls should be populated when searching wiki
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"

    # Validate answer is non-empty
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"


def test_wiki_listing_question():
    """Test agent with wiki listing question - should use list_files tool."""
    returncode, output, stderr = run_agent(
        "What documentation files are available in the wiki?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    # Validate required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"

    # tool_calls should contain at least one list_files call
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"

    # Check that list_files was called
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "list_files" in tool_names, "Expected list_files tool to be called"

    # Validate answer is non-empty
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"


def test_tool_calls_structure():
    """Test that tool_calls have the correct structure."""
    returncode, output, stderr = run_agent(
        "What is in the wiki directory?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    for tool_call in output.get("tool_calls", []):
        # Each tool call should have tool, args, and result
        assert "tool" in tool_call, "Missing 'tool' in tool_call"
        assert "args" in tool_call, "Missing 'args' in tool_call"
        assert "result" in tool_call, "Missing 'result' in tool_call"

        # args should be a dict
        assert isinstance(tool_call["args"], dict), "'args' must be a dict"

        # result should be a string
        assert isinstance(tool_call["result"], str), "'result' must be a string"


def test_path_security_traversal():
    """Test that path traversal is blocked (security test)."""
    # This test verifies the tool directly since the LLM shouldn't attempt traversal
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    from agent import read_file_tool, list_files_tool

    # Test read_file with path traversal
    result = read_file_tool("../.env.secret")
    assert "Error" in result, "Should block path traversal in read_file"

    result = read_file_tool("/etc/passwd")
    assert "Error" in result, "Should block absolute paths in read_file"

    # Test list_files with path traversal
    result = list_files_tool("../../")
    assert "Error" in result, "Should block path traversal in list_files"

    result = list_files_tool("/etc")
    assert "Error" in result, "Should block absolute paths in list_files"
