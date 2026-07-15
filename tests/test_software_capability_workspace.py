from __future__ import annotations

from agentco_capability.tools import ToolDeniedError, execute_tool


def test_fixture_test_runner_executes_allowed_python_tests():
    result = execute_tool(
        "fixture_test_runner",
        {
            "files": {
                "test_sample.py": "def test_ok():\n    assert 2 * 3 == 6\n",
            },
            "test_command": ["python3", "-c", "import test_sample; test_sample.test_ok()"],
        },
        ["fixture_test_runner"],
    )
    assert result["exit_code"] == 0


def test_fixture_test_runner_rejects_unapproved_commands():
    try:
        execute_tool("fixture_test_runner", {"files": {}, "test_command": ["bash", "-lc", "true"]}, ["fixture_test_runner"])
    except ToolDeniedError as exc:
        assert "only permits python" in str(exc)
    else:
        raise AssertionError("workspace command escaped allowlist")


def test_fixture_files_cannot_escape_workspace():
    try:
        execute_tool("fixture_test_runner", {"files": {"../escape.py": "x=1"}, "test_command": ["python3", "-m", "pytest", "-q"]}, ["fixture_test_runner"])
    except ToolDeniedError as exc:
        assert "escapes workspace" in str(exc)
    else:
        raise AssertionError("fixture file escaped workspace")
