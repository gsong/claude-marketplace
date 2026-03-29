# gsong-marketplace

George Song's Claude Code plugin marketplace.

## Installation

Add the marketplace, then install plugins individually:

```
/plugin marketplace add gsong/claude-marketplace
```

## Plugins

### git-tools

Git commit, worktree, and auto-squash skills.

```
/plugin install git-tools@gsong-marketplace
```

**Skills:** `commit`, `worktree`, `auto-squash`

### gh-tools

GitHub CLI PR review, comment posting, triage, and project management skills.

```
/plugin install gh-tools@gsong-marketplace
```

**Skills:** `pr-review`, `post-pr-comments`, `triage-review`, `github-project-manager`

### docs-memory

AI documentation bootstrapping, review, and session memory management.

```
/plugin install docs-memory@gsong-marketplace
```

**Skills:** `init-docs-ai`, `review-docs-ai`, `save-session-memory`, `review-memory`

### codex-tools

OpenAI Codex CLI integration for parallel PR reviews and headless task delegation.

```
/plugin install codex-tools@gsong-marketplace
```

**Skills:** `codex-review`, `run-codex`

### repo-maintenance

Dependency upgrades and CI/CD security auditing for project repositories.

```
/plugin install repo-maintenance@gsong-marketplace
```

**Skills:** `pnpm-upgrade-dependencies`, `pnpm-upgrade`, `zizmor-audit`, `gha-upgrade`

### utilities

General-purpose utilities for Claude Code.

```
/plugin install utilities@gsong-marketplace
```

**Skills:** `date-calculator`

## License

MIT
