# gh-tools

GitHub CLI workflow skills for Claude Code.

## Skills

| Skill                         | Trigger                                        | Description                                       |
| ----------------------------- | ---------------------------------------------- | ------------------------------------------------- |
| `gs:gh-tools:review`          | "review PR", "code review"                     | Comprehensive PR code review with parallel agents |
| `gs:gh-tools:post-comments`   | "post review comments", "post PR comments"     | Post review findings as GitHub PR comments        |
| `gs:gh-tools:triage`          | "triage review", "investigate review findings" | Investigate and triage code review findings       |
| `gs:gh-tools:project-manager` | "project board", "GitHub project"              | Create agents for GitHub project board management |

## Prerequisites

- [GitHub CLI (`gh`)](https://cli.github.com/) — installed and authenticated

### For PR review skills

The `gs:gh-tools:review` skill depends on external plugins:

- `superpowers` — provides the `superpowers:code-reviewer` agent
- `feature-dev` — provides the `feature-dev:code-reviewer` agent

Install them:

```
/plugin install superpowers@claude-plugins-official
/plugin install feature-dev@claude-plugins-official
```

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install gh-tools@gsong-marketplace
```
