# repo-maintenance

Repository maintenance skills for Claude Code — dependency upgrades and CI/CD security auditing.

## Skills

| Skill                         | Trigger                                            | Description                                                 |
| ----------------------------- | -------------------------------------------------- | ----------------------------------------------------------- |
| `/repo-maintenance:pnpm-deps` | "upgrade dependencies", "outdated packages"        | Upgrade project dependencies using pnpm, then run the tests |
| `/repo-maintenance:pnpm`      | "upgrade pnpm"                                     | Upgrade the pnpm version across every project reference     |
| `/repo-maintenance:mise`      | "bump mise tools", "mise outdated"                 | Upgrade mise-managed tool versions in `mise.toml`           |
| `/repo-maintenance:zizmor`    | "zizmor", "audit GitHub Actions workflow security" | Run a zizmor security audit and offer fixes                 |
| `/repo-maintenance:gha`       | "upgrade GitHub Actions", "actions-up"             | Upgrade GitHub Actions dependencies using actions-up        |

## Prerequisites

- [pnpm](https://pnpm.io/) — for dependency upgrades (`pnpm-deps` only; the `pnpm` skill uses `npm view` and file edits, so it doesn't need pnpm installed)
- [mise](https://mise.jdx.dev/) — for upgrading mise-managed tool versions
- [zizmor](https://docs.zizmor.sh/) — for GitHub Actions security auditing
- [gh CLI](https://cli.github.com/), authenticated — provides the GitHub token for `gha`, and for `zizmor`'s online audits (without it, `zizmor` runs `--offline`)
- [Node.js](https://nodejs.org/) with `npx` — runs actions-up for `gha`
- [actions-up](https://github.com/azat-io/actions-up) — for GitHub Actions dependency upgrades (runs via `npx`, no install needed)

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install repo-maintenance@gsong-marketplace
```
