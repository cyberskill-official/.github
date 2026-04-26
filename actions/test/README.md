# 🧪 Test

This action runs the project's test suite with optional coverage upload.

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `COVERAGE` | Whether to upload coverage artifacts | `false` | `false` |
| `COVERAGE_ARTIFACT_NAME` | Name of the coverage artifact | `false` | `coverage` |
| `COVERAGE_THRESHOLD` | Minimum coverage percentage to pass (e.g., '80'). Requires a coverage/coverage-summary.json file. Leave empty to skip. | `false` | `` |
| `RETENTION_DAYS` | Number of days to retain the coverage artifact | `false` | `7` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/test@main
with:
```
