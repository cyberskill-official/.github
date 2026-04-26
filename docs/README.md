# CyberSkill `.github`

[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/cyberskill-official/.github/badge)](https://securityscorecards.dev/viewer/?uri=github.com/cyberskill-official/.github)

Organization-level defaults, **reusable composite actions**, branch/tag rulesets, and community health files for all [CyberSkill](https://github.com/cyberskill-official) repositories.

## 📦 Reusable Actions

All actions live under `actions/` and can be referenced by any repo in the org:

```yaml
uses: cyberskill-official/.github/actions/<action-name>@main
```

| Action | Description | Key Inputs |
| ------ | ----------- | ---------- |
| [`env-deps`](../actions/env-deps) | Sets up pnpm, Node.js, `.env`, and installs dependencies | `NODE_VERSION` (default: `24.14.0`), `PNPM_VERSION` (default: `10.29.3`), `PACKAGE_MANAGER` |
| [`build`](../actions/build) | Runs `pnpm build` and optionally uploads artifacts | `BUILD_ARTIFACT_NAME`, `BUILD_PATH`, `RETENTION_DAYS` |
| [`lint`](../actions/lint) | Runs YAML lint + `pnpm lint` (with optional `SKIP_YAML_LINT` input) | `SKIP_YAML_LINT` |
| [`lint-yaml`](../actions/lint-yaml) | Standalone YAML linting via `yamllint` | — |
| [`test`](../actions/test) | Runs `pnpm test` with optional coverage upload and multi-metric threshold | `COVERAGE`, `COVERAGE_THRESHOLD`, `COVERAGE_ARTIFACT_NAME` |
| [`security-audit`](../actions/security-audit) | Runs `pnpm audit` with configurable severity threshold | `AUDIT_LEVEL` (default: `high`), `OUTPUT_FORMAT` |
| [`deploy`](../actions/deploy) | SSH deploy with health-check and automatic rollback | `HOST`\*, `KEY`\*, `PATH`\*, `BRANCH`\*, `BUILD_COMMAND`, `RELOAD_COMMAND` |
| [`create-pr`](../actions/create-pr) | Creates a pull request via `gh` CLI (idempotent) | `GH_TOKEN`\*, `FROM`\*, `TO`\*, `LABELS`, `ASSIGNEES` |
| [`merge`](../actions/merge) | Merges one branch into another with strategy option | `GH_TOKEN`\*, `FROM`\*, `TO`\*, `CHOOSE_STRATEGY` |
| [`rebase`](../actions/rebase) | Rebases a branch onto another | `GH_TOKEN`\*, `FROM`\*, `TO`\*, `DRY_RUN` |
| [`git-auth`](../actions/git-auth) | Sets up Git identity and token-based URL auth (callers add cleanup step) | `GH_TOKEN`\* |
| [`match-branch`](../actions/match-branch) | Checks branch match and sets `matched` output | `BRANCH`\* |
| [`trigger-events`](../actions/trigger-events) | Fires `repository_dispatch` events with concurrency control | `GH_TOKEN`\*, `REPO`\*, `EVENTS`\*, `MAX_CONCURRENCY` |

\* = required

### Permissions Reference

Minimum GitHub token permissions required by each action:

| Action | Required Permissions |
| ------ | -------------------- |
| `env-deps` | `contents: read` |
| `build` | `contents: read` (+ `actions: write` if uploading artifacts) |
| `lint` | `contents: read` |
| `lint-yaml` | `contents: read` |
| `test` | `contents: read` (+ `actions: write` if uploading coverage) |
| `security-audit` | `contents: read` (+ `actions: write` if uploading report) |
| `deploy` | None (runs on remote SSH server) |
| `create-pr` | `contents: write`, `pull-requests: write` |
| `merge` | `contents: write` |
| `rebase` | `contents: write` |
| `git-auth` | — (sets up auth for subsequent steps) |
| `match-branch` | `contents: read` |
| `trigger-events` | — requires a PAT or GitHub App with `repo` scope |

### Quick Start

A typical CI pipeline using these actions:

```yaml
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2

      - name: Setup environment
        uses: cyberskill-official/.github/actions/env-deps@main

      - name: Security Audit
        uses: cyberskill-official/.github/actions/security-audit@main

      - name: Lint
        uses: cyberskill-official/.github/actions/lint@main

      - name: Test
        uses: cyberskill-official/.github/actions/test@main

      - name: Build
        uses: cyberskill-official/.github/actions/build@main
        with:
          BUILD_ARTIFACT_NAME: my-app
```

## 🛡️ Rulesets

| Ruleset | Scope | Key Rules |
| ------- | ----- | --------- |
| **Tags** (`settings.yml`) | All repos | Deletion protection, non-fast-forward block, SemVer name pattern |
| **Branches** (`rulesets/`) | Per-repo | PR review required, stale review dismissal, linear history |

## 📄 Community Health Files

Default [community health files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file) inherited by all repos:

- [CONTRIBUTING.md](CONTRIBUTING.md) — How to fork, branch, and contribute
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — Contributor Covenant v2.1
- [SECURITY.md](SECURITY.md) — Vulnerability reporting & disclosure policy
- [CONTRIBUTING.md — Releasing](CONTRIBUTING.md#releasing) — How actions are released and versioned
- [ARCHITECTURE.md](ARCHITECTURE.md) — Repository design decisions and directory layout

## 🤖 CI for This Repo

The [CI workflow](../.github/workflows/ci.yml) validates this repo itself:

1. **Validate YAML** — `yamllint` on all YAML files
2. **Validate CODEOWNERS** — Syntax validation for ownership rules
3. **Verify README Sync** — Ensures all actions are documented
4. **Verify Generated Docs** — Ensures generated docs and graphs are up-to-date
5. **Validate Settings Schema** — Validates `settings.yml` structure and values
6. **Validate Changelog Format** — Validates `CHANGELOG.md` structure and version headers
7. **Validate Action Schemas** — `actionlint` on all workflow/action files
8. **Verify SHA Pinning** — Ensures all external `uses:` are pinned to full commit SHAs
9. **Detect Breaking Changes** — Flags removed or newly-required inputs/outputs (override with label)
10. **Dependency Review** — Scans PR dependencies for known vulnerabilities (PR only)
11. **Secret Scanning** — Gitleaks scan for leaked credentials and secrets
12. **Verify Git Auth Cleanup** — Ensures all `git-auth` consumers have `if: always()` cleanup steps
13. **Python Script Tests** — `pytest` for Python scripts and CLI (matrix: 3.10, 3.12, 3.14)
14. **OSSF Scorecard** — Automated supply-chain security scoring
15. **CI Summary** — Posts consolidated status comment to PRs

## 📋 Other Config

| File | Purpose |
| ---- | ------- |
| [`CODEOWNERS`](../CODEOWNERS) | Auto-assigns `@cyberskill-official/core` for reviews |
| [`renovate.json`](../renovate.json) | Automated dependency updates (pnpm + GitHub Actions) |
| [`.yamllint`](../.yamllint) | Shared YAML lint configuration |
| [`.editorconfig`](../.editorconfig) | Consistent editor settings (indent, line endings) |
| [`CHANGELOG.md`](CHANGELOG.md) | Notable changes to actions and configurations |
