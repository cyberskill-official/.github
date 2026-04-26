"""Deploy script logic."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time

from lib.utils import execute

log = logging.getLogger("cyberskill")

ALLOWED_CMDS = {"pnpm", "npm", "yarn", "bun", "pm2", "node", "npx", "make", "docker"}

# Pre-compiled regex for dangerous shell metacharacters/quotes/newlines/backslash.
# Backslash is included to prevent escape-sequence bypass (e.g. \\n, \\t, \\').
_DANGEROUS_METACHAR_RE = re.compile(r'[;|`><$("\'\\\n\r]')


def validate_branch(name: str, value: str) -> None:
    """Validate a Git branch name for safety."""
    if not value:
        log.error("❌ Invalid branch name for %s: must not be empty", name)
        sys.exit(1)
    if value.startswith("-"):
        log.error("❌ Invalid branch name for %s: must not start with '-'", name)
        sys.exit(1)
    if ":" in value:
        log.error("❌ Invalid branch name for %s: must not contain ':'", name)
        sys.exit(1)
    if value.startswith("refs/"):
        log.error("❌ Invalid branch name for %s: must not start with 'refs/'", name)
        sys.exit(1)
    try:
        execute(["git", "check-ref-format", "--branch", value])
    except subprocess.CalledProcessError:
        log.error("❌ Invalid branch name for %s: '%s' is not a valid Git branch", name, value)
        sys.exit(1)


def validate_command(name: str, cmd: str) -> None:
    """Validate a command string against the allowlist and dangerous patterns."""
    if not cmd:
        log.error("❌ %s must not be empty", name)
        sys.exit(1)

    segments = [s.strip() for s in cmd.split("&&")]
    for segment in segments:
        if not segment:
            continue
        tokens = segment.split()
        if not tokens:
            continue
        base_cmd = os.path.basename(tokens[0])
        if base_cmd not in ALLOWED_CMDS:
            log.error("❌ %s contains disallowed command: '%s'. Allowed: %s", name, base_cmd, ALLOWED_CMDS)
            sys.exit(1)

        # check dangerous metacharacters (includes backslash to prevent escape-sequence bypass)
        if _DANGEROUS_METACHAR_RE.search(segment):
            log.error("❌ %s contains shell metacharacters/quotes/newlines in segment: '%s'", name, segment)
            sys.exit(1)


def validate_health_params(retries: str, interval: str) -> tuple[int, int]:
    """Validate health check retry and interval parameters."""
    if not re.match(r"^[1-9][0-9]*$", str(retries)):
        log.error("❌ HEALTH_CHECK_RETRIES must be a positive integer, got: '%s'", retries)
        sys.exit(1)
    if not re.match(r"^[1-9][0-9]*$", str(interval)):
        log.error("❌ HEALTH_CHECK_INTERVAL must be a positive integer, got: '%s'", interval)
        sys.exit(1)
    return int(retries), int(interval)


def validate_deploy_path(deploy_path: str, allowed_paths: str) -> str:
    """Validate and resolve the deploy path against allowed prefixes."""
    if not deploy_path:
        log.error("❌ DEPLOY_PATH must not be empty")
        sys.exit(1)
    if ".." in deploy_path:
        log.error("❌ DEPLOY_PATH must not contain '..' (path traversal)")
        sys.exit(1)

    if not os.path.isabs(deploy_path):
        deploy_path = os.path.join(os.path.expanduser("~"), deploy_path)

    real_path = os.path.realpath(deploy_path)
    allowed_prefixes = [os.path.realpath(p.strip()) for p in allowed_paths.split(",")]

    if not any(real_path.startswith(os.path.join(prefix, "")) or real_path == prefix for prefix in allowed_prefixes):
        log.error("❌ DEPLOY_PATH must be under one of: %s (got: %s)", allowed_paths, real_path)
        sys.exit(1)

    if not os.path.isdir(real_path):
        log.error("❌ DEPLOY_PATH '%s' does not exist or is not a directory", real_path)
        sys.exit(1)

    return real_path


def run_validated_cmd(cmd: str, cwd: str) -> bool:
    """Run a validated command string, splitting on && segments."""
    segments = [s.strip() for s in cmd.split("&&")]
    for segment in segments:
        if not segment:
            continue
        tokens = segment.split()
        try:
            log.info("⏳ Running: %s", segment)
            subprocess.run(tokens, check=True, cwd=cwd)
        except subprocess.CalledProcessError as e:
            log.error("❌ Command failed with exit code %s: %s", e.returncode, segment)
            return False
    return True


def run_health_check(retries: int, interval: int, use_pm2: bool, app_name_filter: str | None = None) -> bool:
    """Run PM2 health check with retries."""
    if not use_pm2:
        log.info("ℹ️  PM2 not detected in deploy commands; skipping PM2 health check.")
        return True

    for attempt in range(1, retries + 1):
        log.info("⏳ Health check attempt %s/%s...", attempt, retries)
        time.sleep(interval)
        try:
            res = execute(["pm2", "jlist"], check=False)
            if not res:
                continue
            data = json.loads(res)
            if app_name_filter:
                online = [
                    x
                    for x in data
                    if x.get("name") == app_name_filter and x.get("pm2_env", {}).get("status") == "online"
                ]
            else:
                online = [x for x in data if x.get("pm2_env", {}).get("status") == "online"]
            if len(online) > 0:
                log.info("✅ Application is online!")
                return True
        except (json.JSONDecodeError, OSError, subprocess.SubprocessError) as e:
            log.warning("⚠️  Health check hit exception: %s", e)
            continue

    return False


def run_deploy(
    path: str,
    branch: str,
    build_cmd: str,
    reload_cmd: str,
    retries: str,
    interval: str,
    allowed_paths: str,
    app_name: str | None = None,
) -> None:
    """Execute a full deployment with validation, build, reload, and health check."""
    # Dep checks — extract base commands from validated command segments
    # to avoid false positives from substrings (e.g. "node_modules" matching "node")
    required_deps = {"git", "jq"}
    dep_candidates = {"pm2", "docker", "node"}
    for cmd_str in (build_cmd, reload_cmd):
        for segment in cmd_str.split("&&"):
            tokens = segment.strip().split()
            if tokens:
                base_cmd = os.path.basename(tokens[0])
                if base_cmd in dep_candidates:
                    required_deps.add(base_cmd)

    for dep in required_deps:
        if shutil.which(dep) is None:
            log.error("❌ Error: '%s' is not installed or not available in PATH.", dep)
            sys.exit(1)

    use_pm2 = "pm2" in required_deps

    validate_branch("DEPLOY_BRANCH", branch)
    validate_command("BUILD_COMMAND", build_cmd)
    validate_command("RELOAD_COMMAND", reload_cmd)
    r_retries, r_interval = validate_health_params(retries, interval)
    deploy_path = validate_deploy_path(path, allowed_paths)

    log.info("🚀 Deploying to %s...", deploy_path)

    # Capture current commit for rollback
    try:
        prev_commit = execute(["git", "rev-parse", "HEAD"], cwd=deploy_path)
    except subprocess.CalledProcessError:
        prev_commit = None

    log.info("⬇️  Fetching latest changes...")
    try:
        execute(
            ["git", "fetch", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}"],
            check=False,
            cwd=deploy_path,
        )
    except subprocess.CalledProcessError:
        execute(["git", "fetch", "origin", branch], cwd=deploy_path)

    try:
        execute(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=deploy_path)
        execute(["git", "checkout", "-q", branch], cwd=deploy_path)
    except subprocess.CalledProcessError:
        try:
            execute(["git", "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{branch}"], cwd=deploy_path)
            execute(["git", "checkout", "-B", branch, "-q", f"origin/{branch}"], cwd=deploy_path)
        except subprocess.CalledProcessError:
            log.info(
                "ℹ️  Branch or ref '%s' not found locally or on origin; falling back to detached FETCH_HEAD",
                branch,
            )
            execute(["git", "checkout", "-q", "FETCH_HEAD"], cwd=deploy_path)

    execute(["git", "reset", "--hard", "FETCH_HEAD"], cwd=deploy_path)

    log.info("📦 Building project...")
    if not run_validated_cmd(build_cmd, cwd=deploy_path):
        log.error("❌ Build failed.")
        sys.exit(1)

    log.info("🔄 Reloading application...")
    if not run_validated_cmd(reload_cmd, cwd=deploy_path):
        log.error("❌ Reload failed.")
        sys.exit(1)

    if not run_health_check(r_retries, r_interval, use_pm2, app_name_filter=app_name):
        log.error("❌ Health check failed! Rolling back to %s...", prev_commit)
        if prev_commit:
            execute(["git", "reset", "--hard", prev_commit], cwd=deploy_path)
            if not run_validated_cmd(build_cmd, cwd=deploy_path):
                log.critical("🚨 CRITICAL: Rollback build failed at %s! Manual intervention required.", prev_commit)
                sys.exit(2)
            if not run_validated_cmd(reload_cmd, cwd=deploy_path):
                log.critical("🚨 CRITICAL: Rollback reload failed at %s! Manual intervention required.", prev_commit)
                sys.exit(2)
            if not run_health_check(r_retries, r_interval, use_pm2, app_name_filter=app_name):
                log.critical(
                    "🚨 CRITICAL: Rollback health check failed at %s! Manual intervention required.",
                    prev_commit,
                )
                sys.exit(2)
            log.warning("⚠️  Rolled back to %s", prev_commit)
        sys.exit(1)

    log.info("✅ Deployment successful!")
