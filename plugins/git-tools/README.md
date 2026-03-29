# git-tools

Git workflow skills for Claude Code.

## Skills

| Skill         | Trigger                                              | Description                                    |
| ------------- | ---------------------------------------------------- | ---------------------------------------------- |
| `commit`      | "commit", "conventional commit"                      | Commit changes with conventional commit format |
| `worktree`    | "worktree", "create worktree"                        | Create git worktrees with intelligent setup    |
| `auto-squash` | "auto-squash", "fixup commits", "distribute changes" | Distribute uncommitted changes via smart fixup |

## Prerequisites

- [pnpm](https://pnpm.io/) — for dependency installation in worktrees

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install git-tools@gsong-marketplace
```
