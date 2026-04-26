"""Tests for scripts/lib/utils.py — the shared execute() function."""

from __future__ import annotations

import os
import subprocess

import pytest
from lib.utils import execute


def test_execute_returns_stripped_stdout():
    """execute() should return stripped stdout from a successful command."""
    result = execute(["echo", "  hello  "])
    assert result == "hello"


def test_execute_returns_empty_string_for_empty_output():
    """execute() should return empty string for a command with no output."""
    result = execute(["true"])
    assert result == ""


def test_execute_raises_on_failure_when_check_true():
    """execute() with check=True should raise CalledProcessError on failure."""
    with pytest.raises(subprocess.CalledProcessError):
        execute(["false"], check=True)


def test_execute_does_not_raise_on_failure_when_check_false():
    """execute() with check=False should not raise on failure."""
    result = execute(["false"], check=False)
    assert result == ""


def test_execute_capture_false_returns_empty():
    """execute() with capture=False should return empty string."""
    result = execute(["echo", "test"], capture=False)
    assert result == ""


def test_execute_with_custom_cwd(tmp_path):
    """execute() should run commands in the specified working directory."""
    result = execute(["pwd"], cwd=str(tmp_path))
    # realpath handles macOS /private/var → /var symlink
    assert os.path.realpath(result) == os.path.realpath(str(tmp_path))


def test_execute_multiline_output_stripped():
    """execute() should strip trailing newlines from multiline output."""
    result = execute(["printf", "line1\\nline2\\n"])
    assert result == "line1\nline2"


def test_execute_rejects_shell_keyword():
    """execute() must not accept shell= parameter (SEC-1: removed to prevent CWE-78)."""
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        execute(["echo", "hello"], shell=True)  # noqa: S604
