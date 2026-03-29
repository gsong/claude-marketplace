# repo-maintenance

Repository maintenance skills for Claude Code — dependency upgrades and CI/CD security auditing.

## Skills

| Skill                       | Trigger                                                        | Description                                           |
| --------------------------- | -------------------------------------------------------------- | ----------------------------------------------------- |
| `pnpm-upgrade-dependencies` | "upgrade dependencies", "update packages", "bump dependencies" | Upgrade project dependencies using pnpm               |
| `pnpm-upgrade`              | "upgrade pnpm", "update pnpm version", "bump pnpm"             | Upgrade pnpm version references across the project    |
| `zizmor-audit`              | "zizmor", "audit GitHub Actions", "security audit workflows"   | Run zizmor security audit on GitHub Actions workflows |
| `gha-upgrade`               | "upgrade actions", "update GitHub Actions", "gha upgrade"      | Upgrade GitHub Actions dependencies using actions-up  |

## Prerequisites

- [pnpm](https://pnpm.io/) — for dependency upgrades
- [zizmor](https://docs.zizmor.sh/) — for GitHub Actions security auditing
- [actions-up](https://github.com/azat-io/actions-up) — for GitHub Actions dependency upgrades (runs via `npx`, no install needed)

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install repo-maintenance@gsong-marketplace
```
