# 🔐 Git Auth

Sets up Git identity and token-based URL authentication for pushing. Compatible with actions/checkout v4–v6. Callers must add their own `if: always()` cleanup step to restore the original remote URL.


## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `GH_TOKEN` | GitHub token for authentication | `true` | — |
| `REPO` | Repository in owner/repo format (defaults to current repo) | `false` | `${{ github.repository }}` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/git-auth@main
with:
  GH_TOKEN: # required
```
