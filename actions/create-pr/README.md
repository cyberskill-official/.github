# 📜 Create PR

This action creates a pull request from the source branch to the target branch

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `GH_TOKEN` | GitHub token for authentication | `true` | — |
| `FROM` | The source branch | `true` | — |
| `TO` | The target branch | `true` | — |
| `TITLE` | Pull Request Title | `false` | `chore(CI): sync changes` |
| `BODY` | Pull Request Body | `false` | `This PR syncs the latest changes.` |
| `SKIP_CHECKOUT` | Skip the checkout step if the repo is already checked out (default: false) | `false` | `false` |
| `LABELS` | Comma-separated labels to apply to the PR (e.g., 'bug,enhancement') | `false` | `` |
| `ASSIGNEES` | Comma-separated GitHub usernames to assign to the PR (e.g., 'user1,user2') | `false` | `` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/create-pr@main
with:
  GH_TOKEN: # required
  FROM: # required
  TO: # required
```
