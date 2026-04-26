# 🔀 Merge

This action merges a source branch into the target branch

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `GH_TOKEN` | GitHub token for authentication | `true` | — |
| `FROM` | The branch to merge from | `true` | — |
| `TO` | The branch to merge into | `true` | — |
| `CHOOSE_STRATEGY` | The strategy to use for the merge | `false` | `theirs` |
| `ALLOW_UNRELATED` | Allow merging unrelated histories (default: false) | `false` | `false` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/merge@main
with:
  GH_TOKEN: # required
  FROM: # required
  TO: # required
```
