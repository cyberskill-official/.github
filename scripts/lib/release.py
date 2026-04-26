"""Release script logic."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

from lib.utils import execute

log = logging.getLogger("cyberskill")


def get_latest_version(changelog: str = "docs/CHANGELOG.md") -> str:
    """Extract the latest versioned release from the changelog."""
    if not os.path.exists(changelog):
        log.error("❌ Could not find %s", changelog)
        sys.exit(1)
    with open(changelog, encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", content, flags=re.MULTILINE)
    if not match:
        log.error("❌ Could not determine latest version from %s", changelog)
        sys.exit(1)
    return match.group(1)


def get_next_version(latest: str, version_arg: str | None) -> str:
    """Calculate the next version based on bump type or explicit version."""
    if version_arg:
        if version_arg in ("major", "minor", "patch"):
            major, minor, patch = map(int, latest.split("."))
            if version_arg == "major":
                return f"{major + 1}.0.0"
            elif version_arg == "minor":
                return f"{major}.{minor + 1}.0"
            else:
                return f"{major}.{minor}.{patch + 1}"
        else:
            if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", version_arg):
                log.error("❌ Invalid version: '%s' (must be SemVer: x.y.z)", version_arg)
                sys.exit(1)
            return version_arg
    else:
        major, minor, patch = map(int, latest.split("."))
        return f"{major}.{minor}.{patch + 1}"


def extract_unreleased_content(changelog: str = "docs/CHANGELOG.md") -> str:
    """Extract content from the [Unreleased] section of the changelog."""
    with open(changelog, encoding="utf-8") as f:
        lines = f.readlines()

    in_unreleased = False
    unreleased_lines = []

    for line in lines:
        if line.startswith("## [Unreleased]"):
            in_unreleased = True
            continue
        if in_unreleased:
            if line.startswith("## ["):
                break
            if line.strip():
                unreleased_lines.append(line.rstrip())

    content = "\n".join(unreleased_lines).strip()
    if not content:
        log.error("❌ [Unreleased] section in %s is empty — nothing to release", changelog)
        sys.exit(1)
    return content


def update_changelog(changelog: str, next_version: str, latest_version: str, date_str: str, repo_url: str) -> None:
    """Update the changelog: stamp [Unreleased] with the new version and add comparison URLs."""
    with open(changelog, encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.startswith("## [Unreleased]"):
            new_lines.append(line)
            new_lines.append("\n")
            new_lines.append(f"## [{next_version}] — {date_str}\n")
        elif line.startswith("[Unreleased]:"):
            new_lines.append(f"[Unreleased]: {repo_url}/compare/v{next_version}...HEAD\n")
            new_lines.append(f"[{next_version}]: {repo_url}/compare/v{latest_version}...v{next_version}\n")
        else:
            new_lines.append(line)

    with open(changelog, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def run_release(version_arg: str | None = None, dry_run: bool = False) -> None:
    """Execute the full release workflow: changelog update, commit, tag, push."""
    changelog = "docs/CHANGELOG.md"
    repo_url = "https://github.com/cyberskill-official/.github"

    if not os.path.exists(changelog):
        log.error("❌ Run this script from the repository root")
        sys.exit(1)

    branch = execute(["git", "branch", "--show-current"])
    if branch != "main":
        log.error("❌ Must be on 'main' branch to release (currently on '%s')", branch)
        sys.exit(1)

    try:
        execute(["git", "diff", "--quiet", "HEAD"])
        status = execute(["git", "status", "--porcelain"])
        if status:
            raise subprocess.CalledProcessError(1, [])
    except subprocess.CalledProcessError:
        log.warning("\n⚠️  You have uncommitted changes:")
        execute(["git", "status", "--short"], capture=False)
        log.info("\nCommit or stash your changes first, then re-run.")
        sys.exit(1)

    latest_version = get_latest_version(changelog)
    log.info("ℹ️  Latest version: v%s", latest_version)

    next_version = get_next_version(latest_version, version_arg)
    log.info("ℹ️  Next version: v%s", next_version)

    if next_version == latest_version:
        log.error("❌ Next version (v%s) is the same as latest (v%s)", next_version, latest_version)
        sys.exit(1)

    unreleased_content = extract_unreleased_content(changelog)

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    log.info("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log.info("  Release: v%s (%s)", next_version, today)
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    log.info("Changes to be released:")
    log.info("%s\n", unreleased_content)

    if dry_run:
        log.info("🔍 DRY RUN — no changes will be made.\n")
        log.info("Would:")
        log.info("  1. Update %s: [Unreleased] → [%s] — %s", changelog, next_version, today)
        log.info("  2. git add + commit: 'chore(release): v%s'", next_version)
        log.info("  3. git tag v%s", next_version)
        log.info("  4. git push origin main --tags")
        sys.exit(0)

    log.info("ℹ️  Updating CHANGELOG...")
    update_changelog(changelog, next_version, latest_version, today, repo_url)
    log.info("✅ CHANGELOG updated")

    log.info("ℹ️  Staging changes...")
    execute(["git", "add", changelog])

    log.info("ℹ️  Committing...")
    execute(["git", "commit", "-m", f"chore(release): v{next_version}"])

    log.info("ℹ️  Tagging v%s...", next_version)
    execute(["git", "tag", "-a", f"v{next_version}", "-m", f"Release v{next_version}"])

    log.info("ℹ️  Pushing to origin...")
    execute(["git", "push", "origin", "main", "--tags"], capture=False)

    log.info("\n✅ Released v%s 🚀", next_version)
    log.info("   Tag: %s/releases/tag/v%s", repo_url, next_version)
    log.info("   Compare: %s/compare/v%s...v%s", repo_url, latest_version, next_version)
