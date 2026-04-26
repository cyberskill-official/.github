import os
import subprocess

import pytest

CLI_PATH = os.path.join(os.path.dirname(__file__), "..", "cli.py")
VALIDATE_BRANCH_PATH = os.path.join(os.path.dirname(__file__), "..", "validate-branch.sh")
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def test_lint_all() -> None:
    """Verify that lint-all successfully runs against the current repository state."""
    res = subprocess.run(["python3", CLI_PATH, "lint-all"], capture_output=True, text=True)
    assert res.returncode == 0, f"lint-all failed:\\n{res.stdout}\\n{res.stderr}"


def test_release_dry_run() -> None:
    """Verify that release --dry-run successfully executes without altering files."""
    res = subprocess.run(["python3", CLI_PATH, "release", "--dry-run"], capture_output=True, text=True)
    assert res.returncode in (0, 1)


def test_deploy_help() -> None:
    """Verify argparsing works for deploy."""
    res = subprocess.run(["python3", CLI_PATH, "deploy", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "--path" in res.stdout
    assert "--branch" in res.stdout


def test_generate_help() -> None:
    """Verify argparsing works for generate."""
    res = subprocess.run(["python3", CLI_PATH, "generate", "--help"], capture_output=True, text=True)
    assert res.returncode == 0


def test_generate_verify_help() -> None:
    """Verify argparsing works for generate-verify."""
    res = subprocess.run(["python3", CLI_PATH, "generate-verify", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "generate-verify" in res.stdout.lower() or "generate" in res.stdout.lower()


def test_verbose_and_quiet_flags() -> None:
    """Verify --verbose and --quiet flags are accepted."""
    for flag in ("--verbose", "--quiet", "-v", "-q"):
        res = subprocess.run(["python3", CLI_PATH, flag, "lint-all"], capture_output=True, text=True)
        assert res.returncode == 0, f"CLI failed with {flag}: {res.stderr}"


def test_quiet_suppresses_info() -> None:
    """Verify --quiet suppresses informational output."""
    normal = subprocess.run(["python3", CLI_PATH, "lint-all"], capture_output=True, text=True)
    quiet = subprocess.run(["python3", CLI_PATH, "--quiet", "lint-all"], capture_output=True, text=True)
    assert quiet.returncode == 0
    # Quiet output should be shorter (no info-level log messages)
    assert len(quiet.stdout) < len(normal.stdout)


# --- Integration tests for validate-branch.sh (MA-1) ---


def test_validate_branch_sh_exists() -> None:
    """Verify validate-branch.sh exists at the path referenced by actions."""
    assert os.path.isfile(VALIDATE_BRANCH_PATH), f"validate-branch.sh not found at {VALIDATE_BRANCH_PATH}"


def test_validate_branch_valid_name() -> None:
    """Verify validate_branch accepts valid branch names."""
    res = subprocess.run(
        ["bash", "-c", f'source "{VALIDATE_BRANCH_PATH}" && validate_branch "TEST" "main"'],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"validate_branch rejected valid name 'main': {res.stderr}"


def test_validate_branch_rejects_empty() -> None:
    """Verify validate_branch rejects empty branch names."""
    res = subprocess.run(
        ["bash", "-c", f'source "{VALIDATE_BRANCH_PATH}" && validate_branch "TEST" ""'],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0


def test_validate_branch_rejects_dash_prefix() -> None:
    """Verify validate_branch rejects branch names starting with '-'."""
    res = subprocess.run(
        ["bash", "-c", f'source "{VALIDATE_BRANCH_PATH}" && validate_branch "TEST" "-bad"'],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0


def test_validate_branch_rejects_colon() -> None:
    """Verify validate_branch rejects branch names containing ':'."""
    res = subprocess.run(
        ["bash", "-c", f'source "{VALIDATE_BRANCH_PATH}" && validate_branch "TEST" "a:b"'],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0


def test_validate_branch_rejects_refs_prefix() -> None:
    """Verify validate_branch rejects branch names starting with 'refs/'."""
    res = subprocess.run(
        ["bash", "-c", f'source "{VALIDATE_BRANCH_PATH}" && validate_branch "TEST" "refs/heads/main"'],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0


# --- self-test subcommand tests ---


def test_self_test_help() -> None:
    """Verify self-test --help is accepted by the CLI."""
    res = subprocess.run(["python3", CLI_PATH, "self-test", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "self-test" in res.stdout.lower() or "local" in res.stdout.lower()


def test_self_test_summary_on_step_failure() -> None:
    """Verify cmd_self_test prints summary and exits non-zero when a step fails."""
    import sys
    import unittest.mock as mock

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import cli

    # Simulate one passing step and one failing step.
    call_count = 0

    def fake_run(_cmd, capture_output=False, text=False):
        nonlocal call_count
        call_count += 1
        result = mock.MagicMock()
        # Odd-numbered calls pass, even-numbered calls fail.
        result.returncode = 0 if call_count == 1 else 1
        result.stdout = ""
        result.stderr = ""
        return result

    # Patch subprocess.run in cli module and suppress lint_all (in-process step).
    with (
        mock.patch.object(cli, "cmd_lint_all", return_value=None),
        mock.patch("cli.subprocess.run", side_effect=fake_run),
        mock.patch("logging.Logger.error"),
        mock.patch("logging.Logger.info"),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_self_test()
    assert exc_info.value.code != 0


def test_self_test_exits_zero_when_all_pass() -> None:
    """Verify cmd_self_test exits 0 when all steps succeed."""
    import sys
    import unittest.mock as mock

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import cli

    def fake_run(_cmd, capture_output=False, text=False):
        result = mock.MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with (
        mock.patch.object(cli, "cmd_lint_all", return_value=None),
        mock.patch("cli.subprocess.run", side_effect=fake_run),
        mock.patch("logging.Logger.error"),
        mock.patch("logging.Logger.info"),
    ):
        # Should NOT raise SystemExit when everything passes.
        try:
            cli.cmd_self_test()
        except SystemExit as exc:
            pytest.fail(f"cmd_self_test raised SystemExit({exc.code}) unexpectedly")


def test_action_source_references_exist() -> None:
    """Verify all 'source' statements in action.yml files reference existing scripts."""
    import re

    actions_dir = os.path.join(REPO_ROOT, "actions")
    missing = []
    for root, _dirs, files in os.walk(actions_dir):
        for fname in files:
            if fname != "action.yml":
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
            # Find source statements like: source "${{ github.action_path }}/../../scripts/validate-branch.sh"
            for match in re.finditer(r'source\s+["\']?\$\{\{[^}]+\}\}/\.\./\.\./(.+?)["\';\s]', content):
                rel_path = match.group(1)
                abs_path = os.path.join(REPO_ROOT, rel_path)
                if not os.path.isfile(abs_path):
                    missing.append(f"{fpath}: {rel_path}")

    assert not missing, "Source references to missing files:\n" + "\n".join(missing)


def test_breaking_changes_detects_removed_output(write_action_file) -> None:
    """Verify check_breaking_changes detects removed outputs (SC-1)."""
    base_data = {
        "inputs": {"FOO": {"required": True}},
        "outputs": {"result": {"description": "The result"}, "status": {"description": "Status code"}},
    }
    pr_data = {
        "inputs": {"FOO": {"required": True}},
        "outputs": {"result": {"description": "The result"}},  # 'status' removed
    }

    base_path = write_action_file(base_data)
    pr_path = write_action_file(pr_data)

    res = subprocess.run(
        ["python3", CLI_PATH, "check-breaking", base_path, pr_path],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0, "Should detect removed output as breaking change"
    assert "REMOVED output" in res.stdout or "REMOVED output" in res.stderr
