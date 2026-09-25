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

**Skills:** `/ai-docs:init`, `/ai-docs:lookup`, `/ai-docs:update`, `/ai-docs:check`, `/ai-docs:audit`

### ai-memory

Session memory and project instruction management for Claude Code.

```
/plugin install ai-memory@gsong-marketplace
```

**Skills:** `/ai-memory:save`, `/ai-memory:review`

### codex-tools

OpenAI Codex CLI integration for parallel PR reviews, task delegation, and multi-round consensus discussions.

```
/plugin install codex-tools@gsong-marketplace
```

**Skills:** `/codex-tools:review`, `/codex-tools:run`, `/codex-tools:discuss`

### gh-tools

GitHub CLI PR review, triage, comment posting, review replies, and project management skills.

```
/plugin install gh-tools@gsong-marketplace
```

**Skills:** `/gh-tools:review`, `/gh-tools:triage`, `/gh-tools:post-comments`, `/gh-tools:address-review`, `/gh-tools:project-manager`

### git-tools

Git commit, worktree, and auto-squash skills.

```
/plugin install git-tools@gsong-marketplace
```

**Skills:** `/git-tools:commit`, `/git-tools:worktree`, `/git-tools:auto-squash`

### repo-maintenance

Dependency upgrades and CI/CD security auditing for project repositories.

```
/plugin install repo-maintenance@gsong-marketplace
```

**Skills:** `/repo-maintenance:pnpm-deps`, `/repo-maintenance:pnpm`, `/repo-maintenance:mise`, `/repo-maintenance:gha`, `/repo-maintenance:zizmor`

### utilities

General-purpose utilities for Claude Code.

```
/plugin install utilities@gsong-marketplace
```

**Skills:** `/utilities:date`

## License

MIT
