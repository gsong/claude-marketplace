# git-workflow

Git and GitHub PR workflow commands for Claude Code.

## Commands

| Command                                | Description                                       |
| -------------------------------------- | ------------------------------------------------- |
| `/git-workflow:commit`                 | Commit changes with conventional commit format    |
| `/git-workflow:pr-review`              | Comprehensive PR code review with parallel agents |
| `/git-workflow:post-pr-comments`       | Post review findings as GitHub PR comments        |
| `/git-workflow:triage-review`          | Investigate and triage code review findings       |
| `/git-workflow:auto-squash`            | Distribute uncommitted changes via smart fixup    |
| `/git-workflow:worktree`               | Create git worktrees with intelligent setup       |
| `/git-workflow:github-project-manager` | Create agents for GitHub project board management |

## Prerequisites

- [GitHub CLI (`gh`)](https://cli.github.com/) — installed and authenticated
- [pnpm](https://pnpm.io/) — for dependency installation in worktrees

### For PR review commands

The `pr-review` command depends on external plugins:

- `superpowers` — provides the `code-reviewer` agent
- `code-review` — provides the `code-review` skill

Install them:

```
/plugin install superpowers@claude-plugins-official
/plugin install code-review@claude-plugins-official
```

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install git-workflow@gsong-marketplace
```
