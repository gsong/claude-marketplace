# git-workflow

Git and GitHub PR workflow skills for Claude Code.

## Skills

| Skill                    | Trigger                                              | Description                                       |
| ------------------------ | ---------------------------------------------------- | ------------------------------------------------- |
| `commit`                 | "commit", "conventional commit"                      | Commit changes with conventional commit format    |
| `pr-review`              | "review PR", "code review"                           | Comprehensive PR code review with parallel agents |
| `post-pr-comments`       | "post review comments", "post PR comments"           | Post review findings as GitHub PR comments        |
| `triage-review`          | "triage review", "investigate review findings"       | Investigate and triage code review findings       |
| `auto-squash`            | "auto-squash", "fixup commits", "distribute changes" | Distribute uncommitted changes via smart fixup    |
| `worktree`               | "worktree", "create worktree"                        | Create git worktrees with intelligent setup       |
| `github-project-manager` | "project board", "GitHub project", "manage project"  | Create agents for GitHub project board management |

## Prerequisites

- [GitHub CLI (`gh`)](https://cli.github.com/) — installed and authenticated
- [pnpm](https://pnpm.io/) — for dependency installation in worktrees

### For PR review skills

The `pr-review` skill depends on external plugins:

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
