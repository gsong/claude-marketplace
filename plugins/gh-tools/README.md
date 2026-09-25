# gh-tools

GitHub CLI workflow skills for Claude Code.

## Skills

| Skill                      | Invoked by                           | Description                                                     |
| -------------------------- | ------------------------------------ | --------------------------------------------------------------- |
| `gh-tools:review`          | you, `/gh-tools:review <pr>`         | Review a PR with parallel reviewers; write findings for triage  |
| `gh-tools:triage`          | you, `/gh-tools:triage <pr>`         | Merge, investigate, and curate findings from all review sources |
| `gh-tools:post-comments`   | you, `/gh-tools:post-comments <pr>`  | Post curated findings as GitHub PR comments                     |
| `gh-tools:address-review`  | you, `/gh-tools:address-review <pr>` | Validate, fix or decline, and reply to each comment on your PR  |
| `gh-tools:project-manager` | "project board", "GitHub project"    | Create agents for GitHub project board management               |

## Prerequisites

- [GitHub CLI (`gh`)](https://cli.github.com/) — installed and authenticated
- Push access to the PR branch — for `/gh-tools:address-review`, which commits and pushes its fixes

### For PR review skills

The `/gh-tools:review` skill depends on external plugins:

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
