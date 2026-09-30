# ai-docs

Full lifecycle AI documentation for Claude Code projects: bootstrap, lookup, update, check, and audit.

## Skills

| Skill             | Description                                                                             |
| ----------------- | --------------------------------------------------------------------------------------- |
| `/ai-docs:init`   | Bootstrap or refresh a `docs-ai/` directory, one per workspace, from code analysis      |
| `/ai-docs:lookup` | Look up project conventions before code changes (read-only, fast)                       |
| `/ai-docs:update` | Update the docs that a code change touched (targeted, lightweight)                      |
| `/ai-docs:check`  | Report which docs are stale relative to their Key Paths (read-only)                     |
| `/ai-docs:audit`  | Audit and clean up every doc: approved edits, a QA pass, and a fresh stamp on every doc |

`lookup` and `update` are model-invoked: Claude can reach them on its own, and the hook points it at them. `init`, `check`, and `audit` are typed by the user.

## Hooks

| Event              | Behavior                                                                                              |
| ------------------ | ----------------------------------------------------------------------------------------------------- |
| `UserPromptSubmit` | Reminds Claude to consult `ai-docs:lookup` before code changes. Silent when no docs directory exists. |

The reminder fires at most once per session (and skips slash commands and very short prompts). When 60% or more of docs still contain `<!-- NEEDS CONTENT` stubs, it instead says most docs need content and suggests populating them before relying on lookups.

## Lifecycle

```
init ──creates──▶ docs-ai/
                       │
update ──updates───────┤  (targeted, after code changes)
                       │
audit ──improves───────┤  (comprehensive sweep)
                       │
check ──diagnoses──────┤  (read-only staleness report)
                       │
lookup ◀──reads────────┘  (convention queries)
```

## Verification Stamp

Every generated doc starts with `<!-- verified-against: [full-commit-sha] -->`. The stamp
records the commit the doc was last generated or verified against. `init`, `update`, and
`audit` write it; `check` and `lookup` use it as the staleness baseline, with the doc's git
timestamp as fallback for unstamped docs.

## Path Resolution

All skills and the hook recognize these docs directory names, in preference order:

1. `docs-ai/`
2. `docs/ai/`
3. `.claude/docs/`

Skills look for them at the working directory and inside workspace packages, so monorepos
resolve. When several candidates exist, a skill picks by the workspace named in the task, then
by where the changed files are, then by the working directory. It then checks that candidate's
topic index and falls through to the others if the topic is missing. Several docs directories
in a monorepo is normal. A skill warns only when two sit at the same path root. The hook finds
every docs directory up to two levels deep. Its reminder names them all, unless the only one is
`docs-ai/` at the project root.

Full rules: [`resources/docs-dir-resolution.md`](resources/docs-dir-resolution.md).

## Shared Resources

Each skill embeds the resources it needs at load time, so one edit changes every skill:

| Resource                                                             | Used by                   |
| -------------------------------------------------------------------- | ------------------------- |
| [`docs-dir-resolution.md`](resources/docs-dir-resolution.md)         | all skills                |
| [`staleness-baseline.md`](resources/staleness-baseline.md)           | `lookup`, `check`         |
| [`doc-writer-brief.md`](resources/doc-writer-brief.md)               | `init`, `update`, `audit` |
| [`verification-stamp.md`](resources/verification-stamp.md)           | `init`, `update`, `audit` |
| [`docs-ai-readme-format.md`](resources/docs-ai-readme-format.md)     | `init`, `audit`           |
| [`project-analysis-prompt.md`](resources/project-analysis-prompt.md) | `init`, `audit`           |

## Installation

```
/plugin install ai-docs@gsong-marketplace
```
