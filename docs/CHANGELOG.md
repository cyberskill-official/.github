# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] — 2026-04-16

### Security
- **scripts/ci-summary.js:** [SEC] Add `{}` to sanitize regex character class to prevent potential template expression injection in dynamic job names. (AUDIT-1776314357-3) (@Agent)
- **scripts/lib/linters.py:** [SEC] Cap `response.read()` to 1MB in `check_integration_ids` to prevent memory exhaustion from unbounded API response. (AUDIT-1776314357-2) (@Agent)
- **scripts/lib/generators.py:** [SEC] Hoist `_esc_pipe` to function scope and apply pipe escaping to output table descriptions, closing defense gap where input descriptions were escaped but output descriptions were not. (AUDIT-1776314357-1) (@Agent)
- **scripts/ci-summary.js:** [SEC] Add null-guard on `c.body` before `.includes()` to prevent TypeError crash when comment body is null. (AUDIT-1776267791-1) (@Agent)
- **scripts/lib/generators.py:** [SEC] Escape pipe characters in markdown table cell values to prevent table structure corruption from untrusted action descriptions. (AUDIT-1776267791-2) (@Agent)

### Added
- **scripts/tests:** [TEST] Add `validate_health_params` leading-zero rejection test (octal-like '07' input). (AUDIT-1776314357-6) (@Agent)
- **scripts/tests:** [TEST] Add `validate_changelog` warning-only path test (missing URL footer returns True). (AUDIT-1776314357-5) (@Agent)
- **scripts/tests:** [TEST] Add 3 unit tests for `check_integration_ids`: no-token skip, HTTP 403 graceful skip, valid app_id validation. (AUDIT-1776314357-4) (@Agent)
- **scripts/tests:** [TEST] Add output pipe-escaping test for `generate_action_docs` verifying table integrity with `|` in output descriptions. (AUDIT-1776314357-1) (@Agent)
- **scripts/tests:** [TEST] Add pipe-escaping test for `generate_action_docs` verifying table integrity with `|` in descriptions/defaults. (AUDIT-1776267791-3) (@Agent)
- **scripts/tests:** [TEST] Add explicit backslash escape-sequence bypass and literal newline injection tests for `validate_command`. (AUDIT-1776267791-4) (@Agent)
- **scripts/tests:** [TEST] Add trailing `&&` empty-segment edge-case test for `run_validated_cmd`. (AUDIT-1776267791-5) (@Agent)
- **scripts/tests:** [TEST] Add subsection-header extraction test for `extract_unreleased_content` covering `### Added`/`### Fixed` parsing. (AUDIT-1776267791-6) (@Agent)
### Security
- **actions/deploy:** [SEC] Quote ${{ github.action_path }} in cp -R command to prevent word-splitting. (AUDIT-1776245734-3) (@Agent)
- **actions/env-deps:** [SEC] Replace direct ${{ inputs.PACKAGE_MANAGER }} interpolation with env var indirection to prevent expression injection. (AUDIT-1776245734-1) (@Agent)
- **scripts/lib/deploy.py:** [SEC] Fix corrupted pre-compiled metacharacter regex that had been split across two physical lines, causing a literal newline to be included in the character class. (AUDIT-1776103694-2) (@Agent)
- **scripts/lib/linters.py:** [SEC] Add `User-Agent` header to GitHub API request in `check_integration_ids` to comply with API policy and prevent throttling. (AUDIT-1776103687-1) (@Agent)
- **scripts/lib/deploy.py:** [SEC] Align tokenizer in `run_validated_cmd` to use `.split()` matching `validate_command`, eliminating parsing differential between validation and execution gates. Remove unused `shlex` import. (AUDIT-1776103694-1) (@Agent)

- **actions/deploy:** [SEC] Replace direct `${{ inputs }}` interpolation with env var indirection to prevent expression injection in credential validation step. (AUDIT-1776101550-1) (@Agent)
- **actions/test:** [SEC] Update stale `upload-artifact` SHA pin from v7.0.0 to v7.0.1 for consistency and security patch coverage. (AUDIT-1776101550-2) (@Agent)
- **scripts/ci-summary.js:** [SEC] Add null-guard on `c.user` to prevent crash when a commenter's GitHub account has been deleted. (AUDIT-1776102226-1) (@Agent)
- **scripts/lib/deploy.py:** [SEC] Add backslash to forbidden metacharacter set in `validate_command` to prevent escape-sequence bypass on remote shell. (AUDIT-1776102226-2) (@Agent)

### Added
- **scripts/tests:** [TEST] Add symlink-bypass test for validate_deploy_path realpath resolution defense. (AUDIT-1776245734-6) (@Agent)
- **scripts/tests:** [TEST] Add 4 unit tests for `run_health_check` covering PM2 skip, online success, retry exhaustion, and app_name filtering. (AUDIT-1776103694-4) (@Agent)
- **scripts/tests:** [TEST] Add 3 unit tests for `get_latest_version` covering valid parse, missing file, and no semver header. (AUDIT-1776103694-3) (@Agent)

- **scripts/tests:** [TEST] Add unit test for `check_breaking_changes` removed-output detection branch. (AUDIT-1776101550-3) (@Agent)
- **scripts/tests:** [TEST] Add edge-case test for `validate_command` empty-string rejection. (AUDIT-1776101550-4) (@Agent)
- **scripts/tests:** [TEST] Add 5 unit tests for Python `validate_branch` covering empty, dash-prefix, colon, and refs/ rejection. (AUDIT-1776102226-3) (@Agent)
- **scripts/tests:** [TEST] Add backslash metacharacter test case for `validate_command`. (AUDIT-1776102226-4) (@Agent)
- **scripts/tests:** [TEST] Add test for `validate_settings` invalid `bypass_mode` branch. (AUDIT-1776102226-5) (@Agent)
- **scripts/tests:** [TEST] Add integration test for `generate_all()` orchestrator function. (AUDIT-1776102226-6) (@Agent)
- **scripts/tests:** [TEST] Add 2 unit tests for `check_readme_actions` covering documented-pass and undocumented-fail branches. (AUDIT-1776103687-5) (@Agent)
- **scripts/tests:** [TEST] Add 2 unit tests for `check_action_readmes` covering present-pass and missing-fail branches. (AUDIT-1776103687-5) (@Agent)

### Fixed
- **scripts/ci-summary.js:** [FIX] Add guard for missing context.issue.number to prevent crash on non-PR triggers. (AUDIT-1776245734-4) (@Agent)
- **pyproject.toml:** [FIX] Revert requires-python from >=3.14.4 to >=3.10 — Renovate erroneously bumped it, breaking CI matrix (3.10/3.12/3.14). (AUDIT-1776245734-2) (@Agent)

- **scripts/tests:** [FIX] Suppress false-positive S108 ruff warning on intentional `/tmp` string argument in `test_validate_deploy_path_empty`. (AUDIT-1776103687-7) (@Agent)

## [1.0.0] — 2026-04-12

### Added

- Unified CLI (`scripts/cli.py`) with lint-all, generate, release, deploy, and self-test commands
- 13 reusable composite GitHub Actions (build, create-pr, deploy, env-deps, git-auth, lint, lint-yaml, match-branch, merge, rebase, security-audit, test, trigger-events)
- CI pipeline with static checks, action schema validation, SHA pin verification, breaking change detection, dependency review, secret scanning, OSSF Scorecard, and Python tests
- CodeQL SAST workflow for Python scripts
- Automated Mermaid dependency graph and per-action README generation
- Branch protection rulesets with SemVer tag enforcement
- Renovate dependency management with auto-merge for non-major updates
- Community health files (CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, ARCHITECTURE)
- Git auth action with extraheader-based token injection and v4–v6 checkout compatibility
- Comprehensive Python test suite (86 tests) covering CLI, deploy, generators, linters, release, and utils

[Unreleased]: https://github.com/cyberskill-official/.github/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/cyberskill-official/.github/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/cyberskill-official/.github/releases/tag/v1.0.0
