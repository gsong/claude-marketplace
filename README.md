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

Find where Clef, Cloudflare's decision model, can make a system's repeated decisions, design an experiment for each fit, and build software that calls Clef.

```
/plugin install clef@gsong-marketplace
```

**Skills:** `/clef:find-opportunities`, `/clef:build`

**Hooks:** `PostToolUse` formats a `clef-opportunities/` record with prettier after each write

**Requires:** Ollama with `clef` or `clef-flash`, or Workers AI, for `build` only. See the [plugin README](plugins/clef/README.md#prerequisites).

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

## Security scanning

CI scans every skill in `plugins/` and `.claude/skills/` with [Cisco skill-scanner](https://github.com/cisco-ai-defense/skill-scanner). It fails on a high or critical finding. The scan runs offline with rules only, so it needs no account and sends nothing out. It runs on every pull request and push to `main`, and a failed scan blocks the merge. The report goes to GitHub code scanning, where medium and low findings show as alerts.

Run the same scan locally:

```
mise run scan:skills
```

Pass a path to also write a SARIF report. The scan reads a copy of the files that git tracks or does not ignore, so ignored files such as `__pycache__` stay out. A local run also reads untracked files, which CI does not have, so it can report findings that CI does not.

To triage a finding:

- A real risk: fix the skill.
- A false positive: add a suppression to `skill-scanner-policy.yaml`. Scope it by `rule_id`, `skills`, and `paths`, and give a reason.
- A rule that can never apply here: add it to `disabled_rules`.

The scan has limits:

- It reads skill directories only. The hook scan below covers plugin hooks, but a script outside `skills/` that no hook runs goes unscanned.
- Rules alone catch 7.7% of malicious skills by Cisco's own count. The scan finds known patterns only, and it does not replace a review.

CI also scans the plugin hooks with `scripts/scan-hooks.py`. The hook scan reads `hooks/hooks.json` and any hooks that `plugin.json` declares. It reads each hook command, and every code file that a command or a scanned file names. It skips files under `skills/`, because the skill scan reads them. It runs in the same CI job as the skill scan, so a failed hook scan also blocks the merge. The CI log lists each file it scanned.

The hook scan fails when a line does one of these things:

- It calls a network tool, such as `curl`, `wget` or `nc`.
- It pipes text into a shell, or into an interpreter that reads its program from the pipe.
- It runs a stream or command output as code, such as `source <(…)` or `eval "$(…)"`.
- It opens a connection through `/dev/tcp/` or `/dev/udp/`.
- It loads a network module, such as Python's `urllib`, Node's `https` or Perl's `LWP`, or calls `fetch`.
- It fetches code or packages, such as `uvx`, `npx`, `npm install`, `pip install`, `git clone`, or a script header that lists dependencies for uv.

It also fails on an `http` hook. It fails on a command that runs a script by a path outside `${CLAUDE_PLUGIN_ROOT}`, or whose script is missing. It fails on a file it cannot read or parse. A whole-line comment does not count. Run the same scan locally:

```
mise run scan:hooks
```

The hook scan has no suppression file. If a hook needs the network, change the rule in `scripts/scan-hooks.py` and say why in the pull request. The hook scan has these limits:

- It matches text only. It does not detect a command name that a script builds at run time.
- It does not detect a hook that runs a script under `skills/`, unless the command names that script through `${CLAUDE_PLUGIN_ROOT}`.
- It checks network use and code fetches only. It does not detect a hook that reads secrets or deletes files.

## License

MIT
