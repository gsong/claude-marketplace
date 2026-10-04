# gsong-marketplace

[![Tests](https://github.com/gsong/claude-marketplace/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/gsong/claude-marketplace/actions/workflows/test.yml?query=branch%3Amain)

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

**Hooks:** `UserPromptSubmit` reminds Claude to consult `ai-docs:lookup` before code changes

### ai-memory

Session memory and project instruction management for Claude Code.

```
/plugin install ai-memory@gsong-marketplace
```

**Skills:** `/ai-memory:save`, `/ai-memory:review`

### clef

Ask Clef, a local decision model, yes/no, pick-one, or rating questions and get a probability with each answer.

```
/plugin install clef@gsong-marketplace
```

**Skills:** `/clef:ask`

**Hooks:** `PreToolUse` approves the skill's calls of `clef.py`

**Requires:** an Apple Silicon Mac, Ollama, uv, and jq. See the [plugin README](plugins/clef/README.md#prerequisites).

### codex-tools

OpenAI Codex CLI integration for parallel PR reviews, task delegation, and multi-round consensus discussions via the codex plugin.

```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex-tools@gsong-marketplace
```

**Skills:** `/codex-tools:review`, `/codex-tools:run`, `/codex-tools:discuss`

**Requires:** Codex CLI and the codex plugin (installs with codex-tools once the `openai-codex` marketplace is added); `review` also needs gh, uv, and the gh-tools directory. See the [plugin README](plugins/codex-tools/README.md#prerequisites).

### gh-tools

GitHub CLI PR review, triage, comment posting, review replies, and project management skills.

```
/plugin install gh-tools@gsong-marketplace
```

**Skills:** `/gh-tools:review`, `/gh-tools:triage`, `/gh-tools:post-comments`, `/gh-tools:address-review`, `/gh-tools:project-manager`

**Requires:** gh CLI; `review` also needs uv and the mattpocock-skills and feature-dev plugins (superpowers optional). See the [plugin README](plugins/gh-tools/README.md#prerequisites).

### git-tools

Git commit, worktree, and auto-squash skills.

```
/plugin install git-tools@gsong-marketplace
```

**Skills:** `/git-tools:commit`, `/git-tools:worktree`, `/git-tools:auto-squash`

**Requires:** pnpm, as the install fallback in worktrees. See the [plugin README](plugins/git-tools/README.md#prerequisites).

### repo-maintenance

Dependency upgrades and CI/CD security auditing for project repositories.

```
/plugin install repo-maintenance@gsong-marketplace
```

**Skills:** `/repo-maintenance:pnpm-deps`, `/repo-maintenance:pnpm`, `/repo-maintenance:mise`, `/repo-maintenance:gha`, `/repo-maintenance:zizmor`

**Requires:** pnpm, mise, zizmor, gh CLI, and Node.js with npx (runs actions-up), each for the skills that use it. See the [plugin README](plugins/repo-maintenance/README.md#prerequisites).

### utilities

General-purpose utilities for Claude Code.

```
/plugin install utilities@gsong-marketplace
```

**Skills:** `/utilities:date`

**Requires:** macOS/BSD `date`.

### writing

Keep text an audience reads in your voice: a drafting pipeline, a send-time lint, a draft gate, and correction capture.

```
/plugin install writing@gsong-marketplace
```

**Skills:** `/writing:draft`

**Hooks:** `PreToolUse` send-time lint and smart-quote check, `PostToolUse` draft gate and correction capture, `Stop` correction promotion

**Requires:** jq, perl, and uv. See the [plugin README](plugins/writing/README.md#requirements).

## License

MIT
