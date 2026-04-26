# 🔍 Match Branch

This action checks if the current branch matches the target branch and sets an output.

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `BRANCH` | Branch to check against | `true` | — |

## Outputs

| Name | Description |
| ---- | ----------- |
| `matched` | 'true' if the current branch matches the target branch, 'false' otherwise |

## Usage

```yaml
uses: cyberskill-official/.github/actions/match-branch@main
with:
  BRANCH: # required
```
