# gh-tools

GitHub CLI workflow skills for Claude Code.

## Skills

| Skill                         | Invoked by                               | Description                                                     |
| ----------------------------- | ---------------------------------------- | --------------------------------------------------------------- |
| `gs:gh-tools:review`          | you, `/gs:gh-tools:review <pr>`          | Comprehensive PR code review with parallel agents               |
| `gs:gh-tools:triage`          | you, `/gs:gh-tools:triage <pr>`          | Merge, investigate, and curate findings from all review sources |
| `gs:gh-tools:post-comments`   | you, `/gs:gh-tools:post-comments <pr>`   | Post curated findings as GitHub PR comments                     |
| `gs:gh-tools:address-review`  | you, `/gs:gh-tools:address-review <pr>`  | Validate, fix or decline, and reply to each comment on your PR  |
| `gs:gh-tools:project-manager` | "project board", "GitHub project"        | Create agents for GitHub project board management               |

## Prerequisites

- [GitHub CLI (`gh`)](https://cli.github.com/) — installed and authenticated

### For PR review skills

The `gs:gh-tools:review` skill depends on external plugins:

- `mattpocock-skills` — provides the `mattpocock-skills:code-review` skill (preferred standards & spec review)
- `feature-dev` — provides the `feature-dev:code-reviewer` agent
- `superpowers` — provides the `superpowers:code-reviewer` agent (optional; fallback when `mattpocock-skills` is not installed)

Install them:

```
/plugin install mattpocock-skills@claude-plugins-official
/plugin install feature-dev@claude-plugins-official
/plugin install superpowers@claude-plugins-official
```

The review pipeline uses a shared findings schema validated by
`plugins/gh-tools/scripts/validate-findings.py` (requires `uv`).

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install gh-tools@gsong-marketplace
```
