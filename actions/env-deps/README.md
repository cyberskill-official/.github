# 🔧 Env & Deps

This action sets up the environment and installs dependencies for the CI pipeline.

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `NODE_VERSION` | Node.js version to use | `false` | `24.14.0` |
| `PNPM_VERSION` | pnpm version to use | `false` | `10.29.3` |
| `PACKAGE_MANAGER` | Package manager to use (pnpm, npm, yarn). Auto-detected if empty. | `false` | `` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/env-deps@main
with:
```
