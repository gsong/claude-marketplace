# repo-maintenance

Repository maintenance skills for Claude Code — dependency upgrades and CI/CD security auditing.

## Skills

| Skill                           | Trigger                                                        | Description                                           |
| ------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------- |
| `gs:repo-maintenance:pnpm-deps` | "upgrade dependencies", "update packages", "bump dependencies" | Upgrade project dependencies using pnpm               |
| `gs:repo-maintenance:pnpm`      | "upgrade pnpm", "update pnpm version", "bump pnpm"             | Upgrade pnpm version references across the project    |
| `gs:repo-maintenance:mise`      | "upgrade mise tools", "bump mise.toml", "mise outdated"        | Upgrade mise-managed tool versions in `mise.toml`     |
| `gs:repo-maintenance:zizmor`    | "zizmor", "audit GitHub Actions", "security audit workflows"   | Run zizmor security audit on GitHub Actions workflows |
| `gs:repo-maintenance:gha`       | "upgrade actions", "update GitHub Actions", "gha upgrade"      | Upgrade GitHub Actions dependencies using actions-up  |

## Prerequisites

- [pnpm](https://pnpm.io/) — for dependency upgrades
- [mise](https://mise.jdx.dev/) — for upgrading mise-managed tool versions
- [zizmor](https://docs.zizmor.sh/) — for GitHub Actions security auditing
- [actions-up](https://github.com/azat-io/actions-up) — for GitHub Actions dependency upgrades (runs via `npx`, no install needed)

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install repo-maintenance@gsong-marketplace
```
