"""Shared test fixtures and helpers for script tests."""

from __future__ import annotations

import subprocess
import sys
from uuid import uuid4

import pytest
import yaml


@pytest.fixture
def write_action_file(tmp_path):
    """Factory fixture to create temp action.yml files with given content."""

    def _write(content: dict) -> str:
        f = tmp_path / f"action_{uuid4().hex[:8]}.yml"
        f.write_text(yaml.dump(content))
        return str(f)

    return _write


@pytest.fixture
def write_action_inputs(write_action_file):
    """Factory fixture to create temp action.yml with given inputs dict."""

    def _write(inputs: dict) -> str:
        return write_action_file({"inputs": inputs})

    return _write


@pytest.fixture
def write_action_steps(write_action_file):
    """Factory fixture to create temp action.yml with given steps list."""

    def _write(steps: list) -> str:
        return write_action_file({"runs": {"using": "composite", "steps": steps}})

    return _write


def run_script(script_path: str, *args: str) -> subprocess.CompletedProcess:
    """Run a Python script and return the CompletedProcess result."""
    return subprocess.run(
        [sys.executable, script_path, *args],
        capture_output=True,
        text=True,
    )
