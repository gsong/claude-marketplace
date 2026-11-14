# repo-maintenance

Dependency upgrades and CI/CD security auditing for project repositories.

## Skills

| Skill                         | Trigger                                            | Description                                                 |
| ----------------------------- | -------------------------------------------------- | ----------------------------------------------------------- |
| `/repo-maintenance:pnpm-deps` | "upgrade dependencies", "outdated packages"        | Upgrade project dependencies using pnpm, then run the tests |
| `/repo-maintenance:pnpm`      | "upgrade pnpm"                                     | Upgrade the pnpm version across every project reference     |
| `/repo-maintenance:mise`      | "bump mise tools", "mise outdated"                 | Upgrade mise-managed tool versions in `mise.toml`           |
| `/repo-maintenance:zizmor`    | "zizmor", "audit GitHub Actions workflow security" | Run a zizmor security audit and offer fixes                 |
| `/repo-maintenance:gha`       | "upgrade GitHub Actions", "actions-up"             | Upgrade GitHub Actions dependencies using actions-up        |

## Prerequisites

- [pnpm](https://pnpm.io/): for `pnpm-deps`. The `pnpm` skill uses `npm view` and file edits, so it does not need pnpm installed.
- [npm](https://www.npmjs.com/): for `pnpm`, which runs `npm view`. It ships with Node.js.
- [mise](https://mise.jdx.dev/): for `mise`.
- [zizmor](https://docs.zizmor.sh/): for `zizmor`.
- [gh CLI](https://cli.github.com/), authenticated: for `gha`, which takes its GitHub token from it. `zizmor` uses it for online audits and runs `--offline` without it.
- [Node.js](https://nodejs.org/) with `npx`: for `gha`, which runs [actions-up](https://github.com/azat-io/actions-up) through `npx` with no separate install.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install repo-maintenance@gsong-marketplace
```
