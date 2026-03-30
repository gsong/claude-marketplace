# gsong-marketplace

George Song's Claude Code plugin marketplace.

## Installation

Add the marketplace, then install plugins individually:

```
/plugin marketplace add gsong/claude-marketplace
```

## Plugins

### ai-docs

Full lifecycle AI documentation for Claude Code projects: bootstrap, lookup, update, check, and audit.

```
/plugin install ai-docs@gsong-marketplace
```

**Skills:** `docs-ai-init`, `docs-ai-lookup`, `docs-ai-update`, `docs-ai-check`, `docs-ai-audit`

### ai-memory

Session memory and project instruction management for Claude Code.

```
/plugin install ai-memory@gsong-marketplace
```

**Skills:** `save-session-memory`, `review-memory`

### codex-tools

OpenAI Codex CLI integration for parallel PR reviews and headless task delegation.

```
/plugin install codex-tools@gsong-marketplace
```

**Skills:** `codex-review`, `run-codex`

### gh-tools

GitHub CLI PR review, comment posting, triage, and project management skills.

```
/plugin install gh-tools@gsong-marketplace
```

**Skills:** `pr-review`, `post-pr-comments`, `triage-review`, `github-project-manager`

### git-tools

Git commit, worktree, and auto-squash skills.

```
/plugin install git-tools@gsong-marketplace
```

**Skills:** `commit`, `worktree`, `auto-squash`

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
