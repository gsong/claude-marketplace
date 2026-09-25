# git-tools

Git workflow skills for Claude Code.

## Skills

| Skill         | Trigger                                                                                    | Description                                    |
| ------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| `commit`      | "commit this", "make a commit", `/git-tools:commit`                                        | Commit changes with conventional commit format |
| `worktree`    | "spin up a worktree", "work on X in parallel", `/git-tools:worktree`                       | Create git worktrees with intelligent setup    |
| `auto-squash` | "fixup my commits", "fold these changes into my earlier commits", `/git-tools:auto-squash` | Distribute uncommitted changes via smart fixup |

## Prerequisites

- [pnpm](https://pnpm.io/) — fallback for dependency installation in worktrees when no lockfile is present (projects with a lockfile use the package manager it indicates)

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install git-tools@gsong-marketplace
```
