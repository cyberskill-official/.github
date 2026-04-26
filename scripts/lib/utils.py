"""Shared utility functions for CLI modules."""

from __future__ import annotations

import subprocess


def execute(cmd: list[str], check: bool = True, capture: bool = True, cwd: str | None = None) -> str:
    """Run a subprocess command and return stripped stdout."""
    res = subprocess.run(cmd, check=check, capture_output=capture, text=True, cwd=cwd)
    return res.stdout.strip() if capture else ""
