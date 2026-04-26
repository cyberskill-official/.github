# 🛠️ Build

This action builds the project

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `BUILD_ARTIFACT_NAME` | Name of the build artifact | `false` | — |
| `BUILD_PATH` | Paths to upload (newline-separated) | `false` | `dist
build
` |
| `RETENTION_DAYS` | Number of days to retain the artifact | `false` | `7` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/build@main
with:
```
