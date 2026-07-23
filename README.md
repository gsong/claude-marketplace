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

**Skills:** `/gs:ai-docs:init`, `/gs:ai-docs:lookup`, `/gs:ai-docs:update`, `/gs:ai-docs:check`, `/gs:ai-docs:audit`

### ai-memory

Session memory and project instruction management for Claude Code.

```
/plugin install ai-memory@gsong-marketplace
```

**Skills:** `/gs:ai-memory:save`, `/gs:ai-memory:review`

### codex-tools

OpenAI Codex CLI integration for parallel PR reviews and headless task delegation.

```
/plugin install codex-tools@gsong-marketplace
```

**Skills:** `/gs:codex-tools:review`, `/gs:codex-tools:run`, `/gs:codex-tools:discuss`

### gh-tools

GitHub CLI PR review, comment posting, triage, and project management skills.

```
/plugin install gh-tools@gsong-marketplace
```

**Skills:** `/gs:gh-tools:review`, `/gs:gh-tools:triage`, `/gs:gh-tools:post-comments`, `/gs:gh-tools:project-manager`

### git-tools

Git commit, worktree, and auto-squash skills.

```
/plugin install git-tools@gsong-marketplace
```

**Skills:** `/gs:git-tools:commit`, `/gs:git-tools:worktree`, `/gs:git-tools:auto-squash`

### repo-maintenance

Dependency upgrades and CI/CD security auditing for project repositories.

```
/plugin install repo-maintenance@gsong-marketplace
```

**Skills:** `/gs:repo-maintenance:pnpm-deps`, `/gs:repo-maintenance:pnpm`, `/gs:repo-maintenance:mise`, `/gs:repo-maintenance:gha`, `/gs:repo-maintenance:zizmor`

### utilities

General-purpose utilities for Claude Code.

```
/plugin install utilities@gsong-marketplace
```

**Skills:** `/gs:utilities:date`

## License

MIT
