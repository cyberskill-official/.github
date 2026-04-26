#!/usr/bin/env bash
# Shared helper functions for GitHub Actions shell scripts.
# Usage: source scripts/lib/helpers.sh (or via $GITHUB_ACTION_PATH)

# Trim leading/trailing whitespace from a string.
# Usage: trimmed=$(trim "  hello  ")
trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s\n' "$s"
}

# Split a comma-separated string into a Bash array.
# Usage: split_csv "a, b, c" result_array
# Requires Bash 4.3+ (nameref support — GitHub-hosted runners use Bash 5.x).
split_csv() {
  local input="$1"
  # shellcheck disable=SC2178
  local -n _csv_ref="$2"
  IFS=',' read -ra _csv_ref <<< "$input"
}

# Validate a value against an allowlist (space-separated).
# Usage: validate_allows_list "value" "opt1 opt2 opt3" "LABEL"
validate_allows_list() {
  local value="$1"
  local allowed="$2"
  local label="${3:-value}"
  for item in $allowed; do
    if [[ "$value" == "$item" ]]; then return 0; fi
  done
  echo "❌ Invalid $label: '$value'. Allowed: $allowed" >&2
  return 1
}

# Retry a command with exponential backoff.
# Usage: retry_with_backoff 3 2 gh api repos/...
retry_with_backoff() {
  local max_attempts="$1"; shift
  local base_delay="$1"; shift
  local attempt
  for attempt in $(seq 1 "$max_attempts"); do
    if "$@"; then return 0; fi
    if [ "$attempt" -lt "$max_attempts" ]; then
      local delay=$((attempt * base_delay))
      echo "⚠️ Retry $attempt/$max_attempts (waiting ${delay}s)" >&2
      sleep "$delay"
    fi
  done
  return 1
}
