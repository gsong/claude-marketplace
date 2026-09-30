# writing

Keep text an audience reads in your voice: a drafting pipeline, a send-time lint, a draft gate, and correction capture.

It covers GitHub text, Slack, email, artifacts, Claude Docs, Google files, and human-facing repo markdown. It also covers `ai-swap/` files you plan to share. Commit messages, code comments, and agent docs keep their own formats.

## Skills

| Skill           | Invoked by                           | Description                                                                             |
| --------------- | ------------------------------------ | --------------------------------------------------------------------------------------- |
| `writing:draft` | Claude, or you with `/writing:draft` | Picks a profile, loads your rules, and runs long pieces through outline and exit passes |

Short items, such as a Slack message or a review comment, skip the pipeline. Claude reads your rules once per session and writes the text. The send-time lint checks it on the way out.

Long items, such as an artifact or a doc, go through fixed stages. Claude drafts them under `ai-swap/drafts/<profile>/`. You approve the outline before any prose exists. Three exit passes follow: humanizer, flow, and accuracy.

## Hooks

| Event         | Hook              | Behavior                                                                                                                                          |
| ------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PostToolUse` | `gate.sh`         | After a write to a draft or to human-facing repo markdown, reports voice violations. For repo markdown it lints only the new text. Advisory only. |
| `PostToolUse` | `capture.sh`      | Logs each edit to a draft next to the instruction that caused it. Silent.                                                                         |
| `Stop`        | `promote.sh`      | Counts the logged corrections. When one pattern recurs, it surfaces that pattern once and asks where it belongs.                                  |
| `PreToolUse`  | `send-lint.sh`    | Lints outgoing text on Slack, Gmail drafts, Claude Docs, Google Drive, artifacts, and `gh` PR and issue text. See below.                          |
| `PreToolUse`  | `smart-quotes.py` | Denies an artifact publish, Slack canvas, Claude Doc, or Google Drive file whose prose holds straight quotes (`'` or `"`).                        |

Most sends get an advisory note. A send you cannot take back is different. That means a Slack message, sent or scheduled, or a `gh` comment, review, or PR body. When the lint finds violations, the send is bounced once. Claude sees the findings before the text goes out. It fixes what is a real violation, or keeps the text, and sends again. The retry always goes through.

A broken lint never blocks a send. Any error in `send-lint` lets the call through.

Repo markdown means any `.md` or `.markdown` file outside `ai-swap/`. The gate skips `CLAUDE.md`, `AGENTS.md`, and `SKILL.md`. It also skips any path with a `skills`, `agents`, `commands`, `references`, `.claude`, `docs-ai`, or `node_modules` segment.

## Rules, references, and state

**Rules** come from the first directory that exists:

1. `$WRITING_LINE_RULES`
2. `~/.claude/writing-line/rules/`
3. The plugin’s own `defaults/rules/`

The first directory found replaces the others whole. Files never merge across directories. That way you can always tell where a rule came from.

**References** hold terms and exemplars. Claude reads `~/.claude/writing-line/references/` first. It then reads `<repo>/.claude/writing-line/references/` if the repo has one. A project term overrides a global term of the same name.

**State** lives in `$WRITING_LINE_STATE`, or `~/.claude/state/writing-line/` by default. It holds the correction log, draft snapshots, and send bounces. It sits outside the plugin on purpose. Uninstalling the plugin leaves your correction history in place.

## Your own rules

The defaults are generic. To write in your own voice, give the plugin your own rules directory:

1. Copy the plugin’s `defaults/rules/` to `~/.claude/writing-line/rules/`.
2. Edit the four files. `common.md` applies to every profile. `comms.md`, `technical.md`, and `mixed.md` each hold one audience.
3. Put voice notes, terms, and exemplars in `~/.claude/writing-line/references/`.

Each rules file has two sections. The **Greppable** block holds the rules the hooks check by pattern. `common.md` documents its field format. The **Judgment** section holds what a pattern cannot catch. Claude reads it before it writes.

Your directory must hold all four files. It replaces the defaults whole, so a missing file is a missing profile.

## Requirements

- `jq`
- `perl` at `/usr/bin/perl`
- [`uv`](https://docs.astral.sh/uv/), for `send-lint.py` and `smart-quotes.py`

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install writing@gsong-marketplace
```
