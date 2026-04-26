# 🚀 Deploy

This action deploys the project to a server using SSH and restarts the PM2 app.

## Inputs

| Name | Description | Required | Default |
| ---- | ----------- | -------- | ------- |
| `HOST` | The host of the server to deploy to | `true` | — |
| `PORT` | The port to connect to the server | `true` | `22` |
| `USERNAME` | The username to connect to the server | `true` | — |
| `PASSWORD` | The password to connect to the server | `false` | — |
| `KEY` | The private key to connect to the server | `false` | — |
| `PASSPHRASE` | The passphrase for the private key | `false` | — |
| `PATH` | The path to the project on the server | `true` | — |
| `BRANCH` | The branch to deploy from | `true` | — |
| `APP_NAME` | PM2 app name for targeted health check. Strongly recommended — without this, the check counts ANY online PM2 process, which may mask a crashed deployment.
 | `false` | — |
| `HEALTH_CHECK_RETRIES` | Number of health check retry attempts | `false` | `5` |
| `HEALTH_CHECK_INTERVAL` | Seconds to wait between health check retries | `false` | `3` |
| `BUILD_COMMAND` | Command to install deps and build the project (runs on remote server). Validation rules: Only allowed base commands: pnpm, npm, yarn, bun, pm2, node, npx, make, docker. Chain with &&. Forbidden characters: quotes (' "), dollar signs ($), semicolons (;), pipes (\|), backticks (`), heredocs (<<), and process substitution (<( )>()). Newlines are also rejected.
 | `false` | `pnpm install --frozen-lockfile && pnpm build` |
| `RELOAD_COMMAND` | Command to reload the application after build (runs on remote server). Same validation rules as BUILD_COMMAND: only allowed base commands (pnpm, npm, yarn, bun, pm2, node, npx, make, docker), chain with &&, no quotes/$/;/\|/`/<</<(/>( characters allowed.
 | `false` | `pm2 startOrReload ecosystem.config.cjs --update-env && pm2 save` |
| `ALLOWED_DEPLOY_PATHS` | Comma-separated list of allowed deploy path prefixes. DEPLOY_PATH is resolved via realpath and must be a subdirectory of one of these prefixes. Path traversal (..) is rejected. Example: '/home,/var/www,/srv'
 | `false` | `/home,/var/www,/srv` |

## Usage

```yaml
uses: cyberskill-official/.github/actions/deploy@main
with:
  HOST: # required
  PORT: # required
  USERNAME: # required
  PATH: # required
  BRANCH: # required
```
