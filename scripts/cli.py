#!/usr/bin/env python3
"""Unified CyberSkill CLI."""

from __future__ import annotations

import argparse
import glob
import inspect
import logging
import subprocess
import sys
from collections.abc import Callable

from lib.deploy import run_deploy
from lib.generators import generate_all
from lib.linters import (
    check_action_readmes,
    check_breaking_changes,
    check_community_health,
    check_integration_ids,
    check_readme_actions,
    validate_changelog,
    validate_codeowners,
    validate_settings,
)
from lib.release import run_release

log = logging.getLogger("cyberskill")


def setup_logging(verbosity: int) -> None:
    """Configure logging based on verbosity: -1=quiet, 0=normal, 1=verbose."""
    levels = {-1: logging.WARNING, 0: logging.INFO, 1: logging.DEBUG}
    level = levels.get(verbosity, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments and return namespace."""
    parser = argparse.ArgumentParser(description="CyberSkill Unified CLI")
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument("--verbose", "-v", action="store_true", help="Enable debug output")
    verbosity_group.add_argument("--quiet", "-q", action="store_true", help="Suppress informational output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy the project via SSH")
    deploy_parser.add_argument("--path", required=True, help="Deploy path")
    deploy_parser.add_argument("--branch", required=True, help="Deploy branch")
    deploy_parser.add_argument("--cmd", required=True, help="Build command")
    deploy_parser.add_argument("--reload", required=True, help="Reload command")
    deploy_parser.add_argument("--retries", default="5", help="Health retries")
    deploy_parser.add_argument("--interval", default="3", help="Health interval")
    deploy_parser.add_argument("--allowed-paths", required=True, help="Allowed path prefixes")
    deploy_parser.add_argument("--app-name", default=None, help="PM2 App name filter")

    # release command
    release_parser = subparsers.add_parser("release", help="Release the project")
    release_parser.add_argument(
        "version",
        nargs="?",
        default=None,
        help="Version (major, minor, patch, or semantic version)",
    )
    release_parser.add_argument("--dry-run", action="store_true", help="Dry run without committing")

    # lint-all command
    lint_all_parser = subparsers.add_parser("lint-all", help="Run all static validations")
    lint_all_parser.add_argument("--fix", action="store_true", help="Attempt to auto-fix issues")

    # check-breaking-changes command
    brk_parser = subparsers.add_parser("check-breaking", help="Check for breaking action changes")
    brk_parser.add_argument("base_file", help="Base action.yml file")
    brk_parser.add_argument("pr_file", help="PR action.yml file")

    # generate command
    subparsers.add_parser("generate", help="Generate docs and diagrams")

    # generate-verify command
    subparsers.add_parser("generate-verify", help="Generate docs/diagrams and verify they are in sync")

    # self-test command
    subparsers.add_parser("self-test", help="Run all local-runnable CI checks")

    return parser.parse_args()


def cmd_lint_all(auto_fix: bool = False) -> None:
    """Run all static validations."""
    success = True
    checks = [
        ("Validating CODEOWNERS", validate_codeowners),
        ("Validating CHANGELOG", validate_changelog),
        ("Validating Settings", validate_settings),
        ("Verifying Integration IDs", check_integration_ids),
        ("Checking Action READMEs", check_action_readmes),
        ("Checking README Actions", check_readme_actions),
        ("Checking Community Health", check_community_health),
    ]
    for label, check_fn in checks:
        log.info("\n=== %s ===", label)
        if "auto_fix" in inspect.signature(check_fn).parameters:
            if not check_fn(auto_fix=auto_fix):
                success = False
        else:
            if not check_fn():
                success = False

    if not success:
        log.error("\n❌ lint-all failed. See errors above.")
        sys.exit(1)
    log.info("\n✅ lint-all passed!")


def cmd_generate_verify() -> None:
    """Generate docs/diagrams and verify nothing changed (for local dev use)."""
    if not generate_all():
        sys.exit(1)
    result = subprocess.run(
        ["git", "diff", "--no-color", "--exit-code"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("❌ Generated files are out of sync. Diff:")
        log.error(result.stdout)
        log.error("Run 'python3 scripts/cli.py generate' and commit the changes.")
        sys.exit(1)
    log.info("✅ All generated files are up-to-date.")


def cmd_self_test() -> None:
    """Run all local-runnable CI checks in sequence with summary output."""
    results: list[tuple[str, bool]] = []

    def run_step(label: str, cmd: list[str]) -> bool:
        log.info("\n🔄 %s ...", label)
        res = subprocess.run(cmd, capture_output=True, text=True)
        passed = res.returncode == 0
        if passed:
            log.info("   ✅ %s passed", label)
        else:
            log.error("   ❌ %s failed", label)
            if res.stdout.strip():
                log.error("%s", res.stdout.strip())
            if res.stderr.strip():
                log.error("%s", res.stderr.strip())
        results.append((label, passed))
        return passed

    def run_python_step(label: str, fn: Callable[[], None]) -> bool:
        log.info("\n🔄 %s ...", label)
        try:
            fn()
            log.info("   ✅ %s passed", label)
            results.append((label, True))
            return True
        except SystemExit:
            log.error("   ❌ %s failed", label)
            results.append((label, False))
            return False

    # 1. lint-all (in-process)
    run_python_step("lint-all", cmd_lint_all)

    # 2. ruff check
    run_step("ruff check", [sys.executable, "-m", "ruff", "check", "scripts/"])

    # 3. ruff format
    run_step("ruff format", [sys.executable, "-m", "ruff", "format", "--check", "scripts/"])

    # 4. yamllint (via pipx or direct)
    run_step("yamllint", ["yamllint", "-c", ".yamllint", "."])

    # 5. shellcheck
    run_step("shellcheck", ["shellcheck"] + glob.glob("scripts/*.sh") + glob.glob("actions/*/*.sh"))

    # 6. pytest
    run_step("pytest", [sys.executable, "-m", "pytest", "scripts/tests/", "-v"])

    # Summary
    log.info("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log.info("  Self-Test Summary")
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    all_passed = True
    for label, passed in results:
        icon = "✅" if passed else "❌"
        log.info("  %s %s", icon, label)
        if not passed:
            all_passed = False
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if all_passed:
        log.info("  ✅ All checks passed!")
    else:
        log.error("  ❌ Some checks failed. See output above.")
        sys.exit(1)


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()
    verbosity = 1 if args.verbose else (-1 if args.quiet else 0)
    setup_logging(verbosity)

    if args.command == "deploy":
        run_deploy(
            args.path,
            args.branch,
            args.cmd,
            args.reload,
            args.retries,
            args.interval,
            args.allowed_paths,
            args.app_name,
        )
    elif args.command == "release":
        run_release(args.version, args.dry_run)
    elif args.command == "lint-all":
        cmd_lint_all(auto_fix=args.fix)
    elif args.command == "check-breaking":
        if not check_breaking_changes(args.base_file, args.pr_file):
            sys.exit(1)
    elif args.command == "generate":
        if not generate_all():
            sys.exit(1)
    elif args.command == "generate-verify":
        cmd_generate_verify()
    elif args.command == "self-test":
        cmd_self_test()


if __name__ == "__main__":
    main()
