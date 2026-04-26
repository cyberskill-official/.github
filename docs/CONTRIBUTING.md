# Contributing

## Request for changes/ Pull Requests
You first need to create a fork of the [.github](https://github.com/cyberskill-official/.github/) repository to commit your changes to it. Methods to fork a repository can be found in the [GitHub Documentation](https://docs.github.com/en/get-started/quickstart/fork-a-repo).

Then add your fork as a local project:

```sh
# Using HTTPS
git clone https://github.com/cyberskill-official/.github.git

# Using SSH
git clone git@github.com:cyberskill-official/.github.git
```

> [Which remote URL should be used ?](https://docs.github.com/en/get-started/getting-started-with-git/about-remote-repositories)

Then, go to your local folder

```sh
cd .github
```

Add git remote controls :

```sh
# Using HTTPS
git remote add fork https://github.com/YOUR-USERNAME/.github.git
git remote add upstream https://github.com/cyberskill-official/.github.git


# Using SSH
git remote add fork git@github.com:YOUR-USERNAME/.github.git
git remote add upstream git@github.com:cyberskill-official/.github.git
```

You can now verify that you have your two git remotes:

```sh
git remote -v
```

## Receive remote updates
In view of staying up to date with the central repository :

```sh
git pull upstream main
```

## Choose a base branch
Before starting development, you need to know which branch to base your modifications/additions on. When in doubt, use main.

| Type of change                |           | Branches              |
| :------------------           |:---------:| ---------------------:|
| Documentation                 |           | `main`              |
| Bug fixes                     |           | `main`              |
| New features                  |           | `main`              |
| New issues models             |           | `main`              |

```sh
# Switch to the desired branch
git switch main

# Pull down any upstream changes
git pull

# Create a new branch to work on
git switch --create patch/1234-name-issue
```

Commit your changes, then push the branch to your fork with `git push -u fork` and open a pull request on [the .github repository](https://github.com/cyberskill-official/.github/) following the template provided.

## Action Development Guide

When adding or modifying shared actions, follow these quality standards:

### Required Elements

- **SHA pinning**: All external `uses:` must be pinned to full 40-character commit SHAs (e.g., `@de0fac2e...`), not floating tags
- **Shell specification**: Every `run:` step must include `shell: bash`
- **Input validation**: Validate all user-provided inputs strictly.
- **Error handling**: Start scripts with `set -euo pipefail`

### Security Hardening

When creating or updating GitHub Actions workflows, always include and retain explicit job-level `permissions` blocks. Never rely on the default broad `GITHUB_TOKEN` permissions.
- **`contents: read`**: Minimum requirement for checking out code.
- **`actions: write`**: Required only if the workflow uploads artifacts (e.g., test coverage, build outputs).

### Naming Convention

- **Action name**: Use emoji prefix + descriptive name (e.g., `🛠️ Build`, `🚀 Deploy`)
- **Input names**: UPPER_SNAKE_CASE (e.g., `BUILD_ARTIFACT_NAME`)
- **File structure**: `actions/<name>/action.yml`

### Pre-commit Hooks (Recommended)

Install [pre-commit](https://pre-commit.com/) to catch lint and formatting issues before push:

```sh
pip install pre-commit
pre-commit install
```

Hooks run automatically on `git commit`. To run all hooks manually:

```sh
pre-commit run --all-files
```

### Testing Locally

You can validate actions locally before pushing:

```sh
# Lint all YAML files
yamllint -c .yamllint .

# Validate action schemas (requires Go)
go install github.com/rhysd/actionlint/cmd/actionlint@v1.7.12
actionlint -color

# Run unified Python CLI linters and tests (requires pytest, ruff, PyYAML)
pip install -r scripts/requirements.txt
python scripts/cli.py lint-all
python scripts/cli.py self-test  # runs all local-runnable CI checks
python -m pytest scripts/tests/ -v
```

### Documentation

- Update `docs/README.md` action table if you add, remove, or rename inputs/outputs
- Add inline comments for non-obvious logic

## Releasing

### How Actions Are Released

This repository uses a **main-branch rolling release** model. All actions reference `@main`:

```yaml
uses: cyberskill-official/.github/actions/<action-name>@main
```

Changes merged to `main` are **immediately available** to all consuming repositories.

### Breaking Changes

Since all repos consume actions from `@main`, breaking changes require coordination:

1. Announce the change in a PR description with `⚠️ BREAKING` label
2. Update all consuming repos in the same PR batch (or coordinate timing)
3. Consider adding backward-compatible input defaults to avoid breakage

### Versioning

> **Note:** The SemVer tags described below are **org-wide tag protection rules** enforced by `settings.yml`. They apply to all CyberSkill repositories that use Git tags for releases (e.g., npm packages, Tauri apps). They are **not** used for consuming these shared actions — actions always reference `@main`.

- **Tags** follow [Semantic Versioning](https://semver.org/) and are enforced by the `settings.yml` rulesets
- Tag protection rules prevent deletion and non-fast-forward updates
- Tag names must match the SemVer pattern (e.g., `1.0.0`, `2.1.0-beta.1`)