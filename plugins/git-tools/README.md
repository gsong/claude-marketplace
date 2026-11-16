# git-tools

Git commit, worktree, and auto-squash skills.

## Skills

| Skill         | Invoked by                                                           | Description                                    |
| ------------- | -------------------------------------------------------------------- | ---------------------------------------------- |
| `commit`      | "commit my changes", `/git-tools:commit`                             | Commit changes with conventional commit format |
| `worktree`    | "spin up a worktree", "work on X in parallel", `/git-tools:worktree` | Create git worktrees with intelligent setup    |
| `auto-squash` | you, `/git-tools:auto-squash [base-branch]`                          | Distribute uncommitted changes via smart fixup |

## Prerequisites

- [git](https://git-scm.com/), for all three skills.
- [pnpm](https://pnpm.io/): the install fallback in worktrees when `package.json` has no lockfile. A project with a lockfile uses the package manager it names (pnpm, npm, yarn, or bun), so that tool must be installed.
- [mise](https://mise.jdx.dev/), only to trust a `mise.toml` in a new worktree.
- [direnv](https://direnv.net/), only to allow an `.envrc` in a new worktree.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install git-tools@gsong-marketplace
```
