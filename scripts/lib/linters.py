"""Linting and static validation checks.

Convention: GitHub Actions workflow commands (::error::, ::warning::) MUST use
print() to reach stdout where GitHub parses them into annotations. All other
output uses the ``log`` logger so it respects --quiet / --verbose flags.
The ``gh_annotation()`` helper below makes this intent explicit.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any

import yaml

log = logging.getLogger("cyberskill")


_ALLOWED_ANNOTATION_LEVELS = frozenset({"error", "warning", "notice"})


def _escape_annotation_data(value: str) -> str:
    """Escape special characters in GitHub Actions workflow-command data.

    GitHub's workflow-command encoding rules require that ``%``, ``\\r``, and
    ``\\n`` are percent-encoded so that the runner can parse the command
    correctly and so that untrusted input cannot inject extra commands.
    """
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def gh_annotation(level: str, message: str) -> None:
    """Emit a GitHub Actions workflow annotation.

    Must use ``print()`` — GitHub only parses ``::error::`` / ``::warning::``
    from stdout, not from the logging module.  This helper makes the intent
    explicit and keeps all annotation calls grep-able.

    ``level`` must be one of ``error``, ``warning``, or ``notice``.
    ``message`` is automatically escaped per GitHub's workflow-command encoding
    rules to prevent injection or parser breakage from ``%``, ``\\r``, or ``\\n``.
    """
    if level not in _ALLOWED_ANNOTATION_LEVELS:
        raise ValueError(f"gh_annotation: level must be one of {sorted(_ALLOWED_ANNOTATION_LEVELS)!r}, got {level!r}")
    print(f"::{level}::{_escape_annotation_data(message)}")


def validate_codeowners(filepath: str = "CODEOWNERS", auto_fix: bool = False) -> bool:
    """Validate CODEOWNERS file syntax."""
    if not os.path.exists(filepath):
        gh_annotation("error", f"{filepath} file not found.")
        return False
    errors = 0
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                gh_annotation("error", f"Invalid CODEOWNERS line (missing owner): {line}")
                errors += 1
            for owner in parts[1:]:
                if not owner.startswith("@") and "@" not in owner:
                    gh_annotation("error", f"Invalid owner format '{owner}' in: {line}")
                    errors += 1
    if errors > 0:
        gh_annotation("error", f"Found {errors} CODEOWNERS syntax error(s)")
        return False
    log.info("✅ CODEOWNERS syntax is valid.")
    return True


def validate_changelog(filepath: str = "docs/CHANGELOG.md", auto_fix: bool = False) -> bool:
    """Validate CHANGELOG.md format (Keep a Changelog structure)."""
    if not os.path.exists(filepath):
        gh_annotation("error", f"{filepath} not found")
        return False
    errors = 0
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    if not re.search(r"^## \[Unreleased\]", content, flags=re.MULTILINE):
        gh_annotation("error", f"{filepath} is missing '## [Unreleased]' section")
        errors += 1

    versions = re.findall(r"^## \[[0-9]+\.[0-9]+\.[0-9]+\]", content, flags=re.MULTILINE)
    if not versions:
        gh_annotation("error", f"{filepath} has no versioned sections (expected ## [x.y.z] format)")
        errors += 1

    if not re.search(r"^\[Unreleased\]:\s+https://", content, flags=re.MULTILINE):
        gh_annotation("warning", f"{filepath} is missing [Unreleased] comparison URL footer")

    if errors > 0:
        gh_annotation("error", f"Found {errors} CHANGELOG format error(s)")
        return False
    log.info("✅ %s format is valid.", filepath)
    return True


VALID_ACTOR_TYPES = {"OrganizationAdmin", "RepositoryRole", "Team", "Integration", "DeployKey"}
VALID_BYPASS_MODES = {"always", "pull_request"}
VALID_ENFORCEMENT_VALUES = {"active", "evaluate", "disabled"}
VALID_RULE_TYPES = {
    "deletion",
    "non_fast_forward",
    "tag_name_pattern",
    "creation",
    "update",
    "required_linear_history",
    "pull_request",
    "required_status_checks",
    "required_deployments",
    "required_signatures",
    "required_code_scanning",
    "commit_message_pattern",
    "commit_author_email_pattern",
    "committer_email_pattern",
    "branch_name_pattern",
}


def validate_settings(filepath: str = "settings.yml", auto_fix: bool = False) -> bool:
    """Validate settings.yml schema (rulesets, actors, rules)."""
    if not os.path.exists(filepath):
        gh_annotation("error", f"{filepath} not found")
        return False
    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "rulesets" not in data:
        gh_annotation("error", f"{filepath} must contain a 'rulesets' key")
        return False

    errors = 0
    for i, ruleset in enumerate(data.get("rulesets", [])):
        name = ruleset.get("name", f"ruleset[{i}]")
        enforcement = ruleset.get("enforcement")
        if enforcement and enforcement not in VALID_ENFORCEMENT_VALUES:
            valid = ", ".join(sorted(VALID_ENFORCEMENT_VALUES))
            msg = f"Ruleset '{name}': invalid enforcement '{enforcement}' (valid: {valid})"
            gh_annotation("error", msg)
            errors += 1

        for bypass in ruleset.get("bypass_actors", []):
            at = bypass.get("actor_type")
            if at and at not in VALID_ACTOR_TYPES:
                gh_annotation("error", f"Ruleset '{name}': invalid actor_type '{at}'")
                errors += 1
            bm = bypass.get("bypass_mode")
            if bm and bm not in VALID_BYPASS_MODES:
                msg = f"Ruleset '{name}': invalid bypass_mode '{bm}' (valid: {', '.join(sorted(VALID_BYPASS_MODES))})"
                gh_annotation("error", msg)
                errors += 1

        for rule in ruleset.get("rules", []):
            rt = rule.get("type")
            if rt not in VALID_RULE_TYPES:
                gh_annotation("error", f"Ruleset '{name}': invalid rule type '{rt}'")
                errors += 1

    if errors > 0:
        gh_annotation("error", f"Found {errors} {filepath} validation error(s)")
        return False
    log.info("✅ %s schema is valid.", filepath)
    return True


def check_integration_ids(
    filepath: str = "settings.yml", org_name: str = "cyberskill-official", auto_fix: bool = False
) -> bool:
    """Validate Integration Actor IDs in settings.yml against GitHub API."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        log.info("GITHUB_TOKEN not set. Skipping integration IDs verification.")
        return True

    url = f"https://api.github.com/orgs/{org_name}/installations"
    req = urllib.request.Request(url)  # noqa: S310
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "cyberskill-ci/1.0")

    installed_app_ids: set[int] = set()
    try:
        with urllib.request.urlopen(req, timeout=15) as response:  # noqa: S310
            data = json.loads(response.read(1_048_576).decode())
            installed_app_ids = {inst["app_id"] for inst in data.get("installations", [])}
    except urllib.error.HTTPError as e:
        log.error("Failed to fetch installations: HTTP %s - %s", e.code, e.reason)
        if e.code in (401, 403, 404):
            log.info(
                "Note: This check requires read-only org access. Ensure the token has "
                "'organization_installations: read'. Skipping check."
            )
            return True
        return False
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        log.error("Failed to fetch installations: %s", e)
        return False

    if not os.path.exists(filepath):
        return True

    with open(filepath, encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    errors = 0
    for ruleset in settings.get("rulesets", []):
        for actor in ruleset.get("bypass_actors", []):
            if actor.get("actor_type") == "Integration" and actor.get("actor_id") is not None:
                app_id = actor["actor_id"]
                if app_id not in installed_app_ids:
                    msg = f"Integration App ID {app_id} in {filepath} is not installed in org {org_name}!"
                    gh_annotation("error", msg)
                    errors += 1
                else:
                    log.info("✅ Integration App ID %s is valid and installed.", app_id)

    if errors > 0:
        return False
    log.info("✅ All Integration Actor IDs in %s are valid.", filepath)
    return True


def get_required_input_names(inputs: dict[str, Any]) -> list[str]:
    """Extract sorted list of required input names."""
    return sorted(name for name, props in inputs.items() if props.get("required", False))


def check_breaking_changes(base_file: str, pr_file: str) -> bool:
    """Detect breaking changes in action inputs and outputs between base and PR."""

    def get_action_data(filepath: str) -> dict[str, Any]:
        with open(filepath, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    try:
        base_data = get_action_data(base_file)
    except FileNotFoundError:
        return True  # action wasn't present in base

    try:
        pr_data = get_action_data(pr_file)
    except FileNotFoundError:
        gh_annotation("warning", f"Action was deleted in this PR: {base_file}")
        return False  # action was removed - could be breaking

    errors = 0

    # Check input breaking changes
    base_inputs = base_data.get("inputs", {}) or {}
    pr_inputs = pr_data.get("inputs", {}) or {}
    base_required = set(get_required_input_names(base_inputs))
    pr_required = set(get_required_input_names(pr_inputs))

    removed_inputs = base_required - pr_required
    for name in sorted(removed_inputs):
        gh_annotation("error", f"REMOVED required input: {name} in {pr_file}")
        errors += 1

    added_inputs = pr_required - base_required
    for name in sorted(added_inputs):
        props = pr_inputs[name]
        if "default" not in props:
            gh_annotation("error", f"ADDED required input without default: {name} in {pr_file}")
            errors += 1

    # Check output breaking changes (SC-1)
    base_outputs = set((base_data.get("outputs", {}) or {}).keys())
    pr_outputs = set((pr_data.get("outputs", {}) or {}).keys())

    removed_outputs = base_outputs - pr_outputs
    for name in sorted(removed_outputs):
        gh_annotation("error", f"REMOVED output: {name} in {pr_file}")
        errors += 1

    return errors == 0


def check_readme_actions(readme_path: str = "docs/README.md", auto_fix: bool = False) -> bool:
    """Verify all actions are documented in README."""
    if not os.path.exists(readme_path):
        gh_annotation("error", f"{readme_path} not found")
        return False

    with open(readme_path, encoding="utf-8") as f:
        readme_content = f.read()

    missing_actions = []
    for action_dir in sorted(glob.glob("actions/*/")):
        action_name = os.path.basename(os.path.normpath(action_dir))
        if action_name not in readme_content:
            missing_actions.append(action_name)

    if missing_actions:
        if auto_fix:
            from lib.generators import generate_all

            log.info("Attempting auto-fix by regenerating docs...")
            if generate_all():
                log.info("✅ Auto-fix successful.")
                return True
            else:
                log.error("❌ Auto-fix failed.")

        for action_name in missing_actions:
            gh_annotation("error", f"Action '{action_name}' is not listed in {readme_path}")
        gh_annotation("error", f"{len(missing_actions)} action(s) missing from README.")
        return False
    log.info("✅ All actions are documented in README.")
    return True


def check_action_readmes(auto_fix: bool = False) -> bool:
    """Verify all actions have a README.md file."""
    errors = 0
    for action_dir in sorted(glob.glob("actions/*/")):
        has_action = os.path.isfile(os.path.join(action_dir, "action.yml")) or os.path.isfile(
            os.path.join(action_dir, "action.yaml")
        )
        if has_action:
            readme_path = os.path.join(action_dir, "README.md")
            if not os.path.isfile(readme_path):
                if auto_fix:
                    log.info("Auto-fixing missing README in %s...", action_dir)
                    with open(readme_path, "w", encoding="utf-8") as f:
                        action_name = os.path.basename(os.path.normpath(action_dir))
                        f.write(f"# {action_name}\n\nTODO: Document this action.\n")
                    if os.path.isfile(readme_path):
                        log.info("✅ Created missing README: %s", readme_path)
                        continue
                gh_annotation("error", f"Missing {readme_path}")
                errors += 1

    if errors > 0:
        return False
    log.info("✅ All actions have a README.md.")
    return True


def check_community_health(auto_fix: bool = False) -> bool:
    """Verify required community health files exist."""
    errors = 0
    required_docs = ["CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "ARCHITECTURE.md"]
    for doc in required_docs:
        path = os.path.join("docs", doc)
        if not os.path.isfile(path):
            gh_annotation("error", f"Missing community health file: {path}")
            errors += 1

    if errors > 0:
        gh_annotation("error", f"{errors} required community health file(s) missing")
        return False
    log.info("✅ All community health files present.")
    return True
