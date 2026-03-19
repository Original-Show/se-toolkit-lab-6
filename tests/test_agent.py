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
    project_root = Path("/home/yaroslav/Documents/prog/software-engineering-toolkit/se-toolkit-lab-6")
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [sys.executable, str(agent_path), question],
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

    assert returncode == 0, f"agent.py failed with: {stderr}"

    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"


def test_merge_conflict_question():
    """Test agent with merge conflict question - should use tools to find answer in wiki."""
    returncode, output, stderr = run_agent(
        "How do I resolve a merge conflict in git?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"


def test_wiki_listing_question():
    """Test agent with wiki listing question - should use list_files tool."""
    returncode, output, stderr = run_agent(
        "What documentation files are available in the wiki?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"

    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "list_files" in tool_names, "Expected list_files tool to be called"

    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"


def test_tool_calls_structure():
    """Test that tool_calls have the correct structure."""
    returncode, output, stderr = run_agent(
        "What is in the wiki directory?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    for tool_call in output.get("tool_calls", []):
        assert "tool" in tool_call, "Missing 'tool' in tool_call"
        assert "args" in tool_call, "Missing 'args' in tool_call"
        assert "result" in tool_call, "Missing 'result' in tool_call"
        assert isinstance(tool_call["args"], dict), "'args' must be a dict"
        assert isinstance(tool_call["result"], str), "'result' must be a string"


def test_path_security_traversal():
    """Test that path traversal is blocked (security test)."""
    project_root = Path("/home/yaroslav/Documents/prog/software-engineering-toolkit/se-toolkit-lab-6")
    sys.path.insert(0, str(project_root))

    from agent import read_file_tool, list_files_tool

    result = read_file_tool("../.env.secret")
    assert "Error" in result, "Should block path traversal in read_file"

    result = read_file_tool("/etc/passwd")
    assert "Error" in result, "Should block absolute paths in read_file"

    result = list_files_tool("../../")
    assert "Error" in result, "Should block path traversal in list_files"

    result = list_files_tool("/etc")
    assert "Error" in result, "Should block absolute paths in list_files"


def test_backend_framework_question():
    """Test agent with backend framework question - should use read_file."""
    returncode, output, stderr = run_agent(
        "What Python web framework does the backend use?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"

    # Should use read_file to find framework info in pyproject.toml or backend files
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file tool to be called for framework question"

    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"


def test_database_items_question():
    """Test agent with database items question - should use query_api."""
    returncode, output, stderr = run_agent(
        "How many items are in the database?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"

    # Should use query_api to fetch live data
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "query_api" in tool_names, "Expected query_api tool to be called for database question"

    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"

def test_unauthenticated_status_code_question():
    """Test agent with unauthenticated status code question - should use query_api with auth: false."""
    returncode, output, stderr = run_agent(
        "What HTTP status code does the API return when you request /items/ without authentication?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"

    # Should use query_api to check status code
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "query_api" in tool_names, "Expected query_api tool to be called for status code question"

    # Check that auth: false was used for unauthenticated request
    tool_calls = output.get("tool_calls", [])
    auth_false_used = any(
        tc.get("tool") == "query_api" and tc.get("args", {}).get("auth") is False
        for tc in tool_calls
    )
    assert auth_false_used, "Expected query_api to be called with auth: false for unauthenticated request"

    # Answer should mention 401 or 403
    answer = output.get("answer", "").lower()
    assert "401" in answer or "403" in answer or "unauthorized" in answer, \
        f"Expected answer to mention 401/403 status code, got: {output.get('answer', '')}"

    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"


def test_bug_diagnosis_question():
    """Test agent with bug diagnosis question - should use query_api and read_file."""
    returncode, output, stderr = run_agent(
        "Query the /analytics/completion-rate endpoint for a lab that has no data (e.g., lab-99). What error do you get?"
    )

    assert returncode == 0, f"agent.py failed with: {stderr}"

    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"

    # Should use both query_api and read_file for bug diagnosis
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "query_api" in tool_names, "Expected query_api tool to be called for bug diagnosis"

    # Answer should mention the error (ZeroDivisionError or division by zero)
    answer = output.get("answer", "").lower()
    assert "zero" in answer or "division" in answer or "error" in answer, \
        f"Expected answer to mention ZeroDivisionError, got: {output.get('answer', '')}"

    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"
