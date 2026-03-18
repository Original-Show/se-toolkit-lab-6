"""
Regression tests for agent.py CLI.

Tests validate that agent.py:
- Outputs valid JSON
- Has required 'answer' and 'tool_calls' fields
- tool_calls is an empty array
- Exits with code 0 on success
"""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with required fields."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    # Run agent.py with a simple test question
    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), "What is 2+2?"],
        capture_output=True,
        text=True,
        cwd=project_root,
        timeout=60,
    )

    # Check exit code
    assert result.returncode == 0, f"agent.py failed with: {result.stderr}"

    # Parse JSON output
    output = json.loads(result.stdout)

    # Validate required fields exist
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"

    # Validate tool_calls is empty array
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"
    assert len(output["tool_calls"]) == 0, "'tool_calls' must be empty for Task 1"

    # Validate answer is non-empty string
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must not be empty"


def test_agent_with_different_questions():
    """Test agent.py with different question formats."""
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    test_questions = [
        "What does REST stand for?",
        "Explain dependency injection in one sentence.",
    ]

    for question in test_questions:
        result = subprocess.run(
            [sys.executable, "-m", "uv", "run", str(agent_path), question],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=60,
        )

        assert result.returncode == 0, f"Failed for question: {question}"

        output = json.loads(result.stdout)
        assert "answer" in output
        assert "tool_calls" in output
        assert output["tool_calls"] == []
