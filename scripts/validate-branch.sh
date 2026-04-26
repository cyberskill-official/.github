#!/usr/bin/env bash
# Shared branch name validation for GitHub Actions.
# Usage: source scripts/validate-branch.sh
#        validate_branch "LABEL" "$branch_value"

validate_branch() {
    local label="$1"
    local value="$2"

    if [[ -z "$value" ]]; then
        echo "❌ Invalid branch name for $label: must not be empty" >&2
        return 1
    fi
    if [[ "$value" == -* ]]; then
        echo "❌ Invalid branch name for $label: must not start with '-'" >&2
        return 1
    fi
    if [[ "$value" == *:* ]]; then
        echo "❌ Invalid branch name for $label: must not contain ':'" >&2
        return 1
    fi
    if [[ "$value" == refs/* ]]; then
        echo "❌ Invalid branch name for $label: must not start with 'refs/'" >&2
        return 1
    fi
    if ! git check-ref-format --branch "$value" >/dev/null 2>&1; then
        echo "❌ Invalid branch name for $label: '$value' is not a valid Git branch" >&2
        return 1
    fi
}
