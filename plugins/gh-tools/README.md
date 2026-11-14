# gh-tools

GitHub CLI PR review, triage, comment posting, review replies, and project management skills.

## Skills

| Skill                      | Invoked by                                     | Description                                                                                         |
| -------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `gh-tools:review`          | you, `/gh-tools:review <pr>`                   | Review a PR with parallel reviewers; write findings for triage                                      |
| `gh-tools:triage`          | you, `/gh-tools:triage <pr>`                   | Merge, investigate, and curate review findings; then post or fix them                               |
| `gh-tools:post-comments`   | you, `/gh-tools:post-comments <pr>`            | Post curated findings as GitHub PR comments                                                         |
| `gh-tools:address-review`  | you, `/gh-tools:address-review <pr>`           | Validate, fix or decline, and reply to each comment on your PR                                      |
| `gh-tools:project-manager` | you, `/gh-tools:project-manager <project-url>` | Generate a `.claude/agents/` agent that moves items on a GitHub project board, from the board's URL |

## Prerequisites

- [GitHub CLI (`gh`)](https://cli.github.com/), installed and authenticated.
- [jq](https://jqlang.github.io/jq/), which `/gh-tools:post-comments` and `/gh-tools:project-manager` call.
- [uv](https://docs.astral.sh/uv/), which runs `scripts/validate-findings.py` for `/gh-tools:review`, `/gh-tools:triage` and `/gh-tools:post-comments`.
- Push access to the PR branch, for `/gh-tools:address-review`, which commits and pushes its fixes.
- The `project` scope on your `gh` login, for `/gh-tools:project-manager`. Add it with `gh auth refresh -s project`.

### For `/gh-tools:review`

The skill uses these external plugins:

- `mattpocock-skills` provides the `mattpocock-skills:code-review` skill, the preferred standards and spec review.
- `feature-dev` provides the `feature-dev:code-reviewer` agent.
- `superpowers` provides the `superpowers:code-reviewer` agent. It is optional, a fallback when `mattpocock-skills` is not installed.

Install them:

```
/plugin install mattpocock-skills@claude-plugins-official
/plugin install feature-dev@claude-plugins-official
/plugin install superpowers@claude-plugins-official
```

### Optional

The `writing` plugin. When its `writing:draft` skill is available, `review`, `triage`, `post-comments` and `address-review` run their comment bodies through its draft gate first.

The review skills share a findings schema, which `scripts/validate-findings.py` checks.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install gh-tools@gsong-marketplace
```
