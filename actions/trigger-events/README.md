# 🔥 Trigger Events

This action triggers multiple events for a single repository

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `GH_TOKEN` | GitHub token for authentication | `true` | — |
| `REPO` | Repository to trigger events for | `true` | — |
| `EVENTS` | Comma-separated list of event types to trigger (alphanumeric, hyphens, underscores only) | `true` | — |
| `MAX_CONCURRENCY` | Maximum number of concurrent event dispatches | `false` | `10` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/trigger-events@main
with:
  GH_TOKEN: # required
  REPO: # required
  EVENTS: # required
```
