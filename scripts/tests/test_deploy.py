"""Tests for deploy script validation functions."""

import os
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

import pytest
from lib.deploy import (
    run_health_check,
    run_validated_cmd,
    validate_branch,
    validate_command,
    validate_deploy_path,
    validate_health_params,
)

# ---------------------------------------------------------------------------
#  validate_branch
# ---------------------------------------------------------------------------


def test_validate_branch_valid():
    """Test valid branch names are accepted."""
    validate_branch("TEST", "main")
    validate_branch("TEST", "feature/my-branch")


def test_validate_branch_empty():
    """Test empty branch name is rejected."""
    with pytest.raises(SystemExit):
        validate_branch("TEST", "")


def test_validate_branch_dash_prefix():
    """Test branch names starting with '-' are rejected (prevents git option injection)."""
    with pytest.raises(SystemExit):
        validate_branch("TEST", "-bad")


def test_validate_branch_colon():
    """Test branch names containing ':' are rejected."""
    with pytest.raises(SystemExit):
        validate_branch("TEST", "a:b")


def test_validate_branch_refs_prefix():
    """Test branch names starting with 'refs/' are rejected."""
    with pytest.raises(SystemExit):
        validate_branch("TEST", "refs/heads/main")


# ---------------------------------------------------------------------------
#  validate_command
# ---------------------------------------------------------------------------


def test_validate_command_valid():
    """Test valid commands pass."""
    validate_command("BUILD", "npm run build")
    validate_command("RELOAD", "pm2 restart all")
    validate_command("BUILD", "yarn install && yarn build")


def test_validate_command_invalid_bases():
    """Test unallowed base commands fail."""
    with pytest.raises(SystemExit):
        validate_command("BUILD", "rm -rf /")

    with pytest.raises(SystemExit):
        validate_command("BUILD", "echo 'hello'")


def test_validate_command_empty():
    """Test empty command is rejected."""
    with pytest.raises(SystemExit):
        validate_command("BUILD", "")


def test_validate_command_metacharacters():
    """Test commands with dangerous shell metacharacters fail."""
    dangerous = [
        "npm run build ; ls",
        "npm run build | tee out",
        "npm run build `whoami`",
        "yarn install && pm2 restart $(whoami)",
        "pm2 start 'app'",
        'pm2 start "app"',
        "pm2 start > out",
        "npm run build\\nmalicious",
    ]
    for cmd in dangerous:
        with pytest.raises(SystemExit):
            validate_command("BUILD", cmd)


def test_validate_command_backslash_escape_bypass():
    """Explicit test: backslash must be rejected to prevent escape-sequence bypass (e.g. \\t, \\n, \\')."""
    with pytest.raises(SystemExit):
        validate_command("BUILD", "npm run build\\t--flag")


def test_validate_command_literal_newline_injection():
    """Explicit test: literal newline in command must be rejected to prevent command injection."""
    with pytest.raises(SystemExit):
        validate_command("BUILD", "npm run build\nrm -rf /")


def test_validate_health_params():
    """Test health check params parsing."""
    r, i = validate_health_params("5", "3")
    assert r == 5
    assert i == 3

    with pytest.raises(SystemExit):
        validate_health_params("0", "3")

    with pytest.raises(SystemExit):
        validate_health_params("5", "-1")

    with pytest.raises(SystemExit):
        validate_health_params("abc", "1")


def test_validate_deploy_path_valid(tmp_path):
    """Test valid deploy paths pass resolution."""
    d1 = tmp_path / "app"
    d1.mkdir()
    d2 = tmp_path / "other"
    d2.mkdir()

    allowed = f"{tmp_path}/app,{tmp_path}/other"
    res = validate_deploy_path(str(d1), allowed)
    assert res == str(d1.resolve())


def test_validate_deploy_path_traversal(tmp_path):
    """Test path traversal detection."""
    with pytest.raises(SystemExit):
        validate_deploy_path("../foo", str(tmp_path))


def test_validate_deploy_path_traversal_embedded(tmp_path):
    """Test path traversal detection with .. embedded in a deeper path."""
    with pytest.raises(SystemExit):
        validate_deploy_path(f"{tmp_path}/safe/../etc", str(tmp_path))


def test_validate_deploy_path_empty():
    """Test empty deploy path is rejected."""
    with pytest.raises(SystemExit):
        validate_deploy_path("", "/tmp")  # noqa: S108


def test_validate_deploy_path_not_allowed(tmp_path):
    """Test deploy paths outside allowed prefixes fail."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    unallowed = tmp_path / "unallowed"
    unallowed.mkdir()

    with pytest.raises(SystemExit):
        validate_deploy_path(str(unallowed), str(allowed))


def test_validate_deploy_path_not_exist(tmp_path):
    """Test non-existent deploy paths fail."""
    d1 = tmp_path / "app"
    with pytest.raises(SystemExit):
        validate_deploy_path(str(d1), str(tmp_path))


@patch("lib.deploy.subprocess.run")
def test_run_validated_cmd_success(mock_run):
    """Test run_validated_cmd correctly parses and executes segments."""
    # mock success
    assert run_validated_cmd("npm ci && pnpm build", "/cwd") is True
    assert mock_run.call_count == 2
    mock_run.assert_any_call(["npm", "ci"], check=True, cwd="/cwd")
    mock_run.assert_any_call(["pnpm", "build"], check=True, cwd="/cwd")


@patch("lib.deploy.subprocess.run")
def test_run_validated_cmd_failure(mock_run):
    """Test run_validated_cmd aborts on first failure."""
    mock_run.side_effect = [None, subprocess.CalledProcessError(1, ["pnpm", "build"])]
    assert run_validated_cmd("npm ci && pnpm build && echo skipped", "/cwd") is False
    assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
#  run_health_check
# ---------------------------------------------------------------------------


def test_run_health_check_skips_when_no_pm2():
    """Health check should return True immediately when PM2 is not used."""
    assert run_health_check(retries=3, interval=0, use_pm2=False) is True


@patch("lib.deploy.time.sleep")
@patch("lib.deploy.execute")
def test_run_health_check_succeeds_on_online_app(mock_execute, mock_sleep):
    """Health check should return True when PM2 reports an online process."""
    mock_execute.return_value = json.dumps([{"name": "web", "pm2_env": {"status": "online"}}])
    assert run_health_check(retries=3, interval=1, use_pm2=True) is True
    mock_sleep.assert_called_once_with(1)


@patch("lib.deploy.time.sleep")
@patch("lib.deploy.execute")
def test_run_health_check_fails_after_retries(mock_execute, mock_sleep):
    """Health check should return False after exhausting retries with no online apps."""
    mock_execute.return_value = json.dumps([{"name": "web", "pm2_env": {"status": "errored"}}])
    assert run_health_check(retries=2, interval=1, use_pm2=True) is False
    assert mock_sleep.call_count == 2


@patch("lib.deploy.time.sleep")
@patch("lib.deploy.execute")
def test_run_health_check_filters_by_app_name(mock_execute, mock_sleep):
    """Health check with app_name_filter should only match that specific app."""
    mock_execute.return_value = json.dumps(
        [
            {"name": "other", "pm2_env": {"status": "online"}},
            {"name": "target", "pm2_env": {"status": "errored"}},
        ]
    )
    # 'other' is online but filter requires 'target' — should fail
    assert run_health_check(retries=1, interval=0, use_pm2=True, app_name_filter="target") is False


def test_validate_deploy_path_symlink_bypass(tmp_path):
    """Test symlink-based path traversal is blocked by realpath resolution."""
    # Create the "allowed" directory and a "secret" directory outside it
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    secret = tmp_path / "secret"
    secret.mkdir()

    # Create a symlink inside "allowed" that points to "secret"
    symlink = allowed / "escape"
    symlink.symlink_to(secret)

    # The symlink resolves to tmp_path/secret which is outside the allowed prefix
    with pytest.raises(SystemExit):
        validate_deploy_path(str(symlink), str(allowed))


@patch("lib.deploy.subprocess.run")
def test_run_validated_cmd_trailing_ampersand(mock_run):
    """Trailing '&&' produces an empty segment that must be silently skipped."""
    assert run_validated_cmd("npm ci &&", "/cwd") is True
    # Only one real segment should be executed; the trailing empty one is skipped
    assert mock_run.call_count == 1
    mock_run.assert_called_once_with(["npm", "ci"], check=True, cwd="/cwd")


def test_validate_health_params_rejects_leading_zero():
    """Octal-like inputs like '07' must be rejected — regex requires [1-9] as first digit."""
    with pytest.raises(SystemExit):
        validate_health_params("07", "3")

    with pytest.raises(SystemExit):
        validate_health_params("5", "03")
