# 🛡️ Security Audit

This action runs a security audit on project dependencies.

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `AUDIT_LEVEL` | Minimum vulnerability level to fail on (low, moderate, high, critical) | `false` | `high` |
| `OUTPUT_FORMAT` | Output format for audit results (text, json). When 'json', results are saved as an artifact. | `false` | `text` |
| `OUTPUT_ARTIFACT` | Name of the artifact to upload audit results to (only used when OUTPUT_FORMAT is 'json') | `false` | `security-audit-report` |
| `RETENTION_DAYS` | Number of days to retain the audit artifact | `false` | `30` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/security-audit@main
with:
```
