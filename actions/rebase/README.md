# 🔀 Rebase

This action rebases a source branch onto the target branch

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `GH_TOKEN` | GitHub token for authentication | `true` | — |
| `FROM` | The branch to rebase from | `true` | — |
| `TO` | The branch to rebase into | `true` | — |
| `DRY_RUN` | If 'true', only shows what would happen without actually pushing | `false` | `false` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/rebase@main
with:
  GH_TOKEN: # required
  FROM: # required
  TO: # required
```
