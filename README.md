# gsong-marketplace

[![Tests](https://github.com/gsong/claude-marketplace/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/gsong/claude-marketplace/actions/workflows/test.yml?query=branch%3Amain)

George Song's Claude Code plugin marketplace.

## Installation

Add the marketplace, then install each plugin you want:

```
/plugin marketplace add gsong/claude-marketplace
/plugin install <plugin>@gsong-marketplace
```

Each plugin's README lists its skills, its hooks and its prerequisites. Read it before you install: some plugins need other tools or another marketplace first.

## Plugins

| Plugin                                                 | What it does                                                                                                                           |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| [ai-docs](plugins/ai-docs/README.md)                   | Full lifecycle AI documentation for Claude Code projects: bootstrap, lookup, update, check, and audit.                                 |
| [ai-memory](plugins/ai-memory/README.md)               | Session memory and project instruction management for Claude Code.                                                                     |
| [browser](plugins/browser/README.md)                   | Drive a real Google Chrome with agent-browser, on a repo's persistent profile or a throwaway one.                                      |
| [clef](plugins/clef/README.md)                         | Build software with Clef, Cloudflare's decision model, run locally through Ollama or on Workers AI.                                    |
| [cloudflare](plugins/cloudflare/README.md)             | Change and read a Cloudflare account from Claude Code: wrangler first, then the API with a token kept in 1Password.                    |
| [codex-tools](plugins/codex-tools/README.md)           | OpenAI Codex CLI integration for parallel PR reviews, task delegation, and multi-round consensus discussions via the codex plugin.     |
| [cowork](plugins/cowork/README.md)                     | Make a Claude Code plugin also work in Cowork, on Claude Desktop and claude.ai: packaging, browsers, state, and what each plan allows. |
| [gh-tools](plugins/gh-tools/README.md)                 | GitHub CLI PR review, triage, comment posting, review replies, and project management skills.                                          |
| [git-tools](plugins/git-tools/README.md)               | Git commit, worktree, and auto-squash skills.                                                                                          |
| [repo-maintenance](plugins/repo-maintenance/README.md) | Dependency upgrades and CI/CD security auditing for project repositories.                                                              |
| [typescript7-lsp](plugins/typescript7-lsp/README.md)   | TypeScript 7 code intelligence through the language server built into tsc.                                                             |
| [utilities](plugins/utilities/README.md)               | General-purpose utilities for Claude Code.                                                                                             |
| [writing](plugins/writing/README.md)                   | Keep text an audience reads in your voice: a drafting pipeline, a send-time lint, a draft gate, and correction capture.                |

## Security scanning

CI runs two scans on every pull request and push to `main`, and a failed scan blocks the merge:

- The skill scan runs Cisco skill-scanner on every skill in `plugins/` and `.claude/skills/`.
- The hook scan reads each plugin hook, and the code files it names, for network use and downloads.

Run both locally:

```
mise run scan:skills
mise run scan:hooks
```

[Security scanning](docs/security-scanning.md) covers how to triage a finding, what the hook scan fails on, and the limits of each scan.

## License

MIT
