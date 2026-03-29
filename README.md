# gsong-marketplace

George Song's Claude Code plugin marketplace.

## Installation

Add the marketplace, then install plugins individually:

```
/plugin marketplace add gsong/claude-marketplace
```

## Plugins

### git-workflow

Git commit, PR review, worktree, auto-squash, and GitHub project management commands.

```
/plugin install git-workflow@gsong-marketplace
```

**Commands:** `commit`, `pr-review`, `post-pr-comments`, `triage-review`, `auto-squash`, `worktree`, `github-project-manager`

### docs-memory

AI documentation bootstrapping, review, and session memory management.

```
/plugin install docs-memory@gsong-marketplace
```

**Commands:** `init-docs-ai`, `review-docs-ai`, `save-session-memory`, `review-memory`

### codex-tools

OpenAI Codex CLI integration for parallel PR reviews and headless task delegation.

```
/plugin install codex-tools@gsong-marketplace
```

**Skills:** `codex-review`, `run-codex`

### utilities

Date calculator, dependency upgrades, and GitHub Actions security auditing.

```
/plugin install utilities@gsong-marketplace
```

**Skills:** `date-calculator` | **Commands:** `upgrade-dependencies`, `zizmor-audit`

## License

MIT
