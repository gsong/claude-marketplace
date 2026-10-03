---
name: "draft"
description: "Voice pipeline for text an audience reads. Use when writing or revising a PR body, review comment, Slack message, email, artifact, Claude Doc, Google file, human-facing repo markdown, or an ai-swap/ file meant for sharing. Commit messages, code comments, and agent docs keep their own formats."
---

# Draft

Text an audience reads goes out in the user's voice. The hooks check the mechanics. This skill carries what they cannot: the profile, the references, the approvals, and the exit passes.

Hooks that run on their own:

- **gate** reports voice violations after every write to a draft, and after every edit to human-facing repo markdown.
- **capture** logs each draft edit against the instruction that caused it. **promote** surfaces repeated corrections at the end of a turn.
- **send-lint** lints outgoing text before a send. It bounces a send that cannot be taken back (a Slack message, a `gh` comment or PR body) once.
- **smart-quotes** denies an HTML artifact, Claude Doc, Google file, or Slack canvas whose prose has straight quotes. Write ’ “ ” on those surfaces from the start. Markdown files keep straight quotes.

## 1. Pick the route and the profile

| Surface                                                           | Route | Profile                                              |
| ----------------------------------------------------------------- | ----- | ---------------------------------------------------- |
| Slack message, email reply saved as a Gmail draft                 | short | `comms`                                              |
| PR body, review comment, other GitHub text                        | short | `technical`                                          |
| Small edit to existing repo markdown                              | short | `technical`                                          |
| Drafted email or announcement the user reviews before it goes     | long  | `comms`                                              |
| Artifact, Claude Doc, Google file, new or rewritten repo markdown | long  | `technical`, or `mixed` for a non-technical audience |
| `ai-swap/` file meant for sharing                                 | long  | as for a document                                    |

Ask with AskUserQuestion when the surface fits no row, when the audience might be non-technical, or when it is unclear whether an `ai-swap/` file will be shared. An `ai-swap/` file that stays with you is scratch, and this skill ends there.

Done when the route and the profile are set.

## 2. Load the rules and references

The rules directory is the first that exists: `$WRITING_LINE_RULES`, `~/.claude/writing-line/rules/`, `${CLAUDE_PLUGIN_ROOT}/defaults/rules/`. The first one found replaces the others whole.

Read, in this order:

1. `<rules>/<profile>.md`, the Judgment section. The Greppable block belongs to the hooks.
2. Every file in `~/.claude/writing-line/references/`: the terms that hold everywhere.
3. Every file in `<repo>/.claude/writing-line/references/`, if the repo has one. A project term overrides a global term of the same name.

The short route loads each profile once per session, before its first item. The long route loads it for every draft.

Done when the Judgment section and every reference file are read.

## Short route

Write the text to the loaded rules and send it. send-lint reads it on the way out. A repo markdown edit is written in place, and the gate reads the new text. An email sent from the shell, such as `gws gmail +reply`, is never linted, so save it as a Gmail draft instead.

- An advisory report arrives after the send. Fix a real violation in a follow-up edit if the surface allows one.
- A bounce is expected, not a failure. Read the findings, fix what is a real violation or keep the text as is, and send again within 30 minutes. A later retry is bounced again.

## Long route

A draft goes through fixed stages. Each stage ends with the user.

The draft path arms the hooks:

    <repo>/ai-swap/drafts/<profile>/    when the writing belongs to a project
    ~/ai-swap/drafts/<profile>/         otherwise

### 3. Agree the promise — `mixed` only

Write three headline and subhead candidates. Score each against:

- Does it name a concrete outcome, not a topic?
- Would the audience recognize the problem in the first line?
- Does it promise something the draft can deliver?

Put the candidates to the user with AskUserQuestion. The user picks.

### 4. Agree the outline — `technical` and `mixed`

Write the full spine before any prose: every section, one line on what each does, and the evidence each claim will rest on.

Put it to the user and wait for approval. Prose starts after it. An outline is cheap to change. A draft is not.

`comms` goes from stage 2 straight to the draft. A message has no spine to agree.

### 5. Draft

Write it. The gate reports on every write. Fix real violations on your next turn. When a rule misreads the same passage twice, say so: the rule is wrong, and the user can retire it.

Done when the draft is whole and the gate's last report holds no real violation.

### 6. The three exit passes

Run them in this order, one at a time. Each pass reads the whole draft.

**Humanizer.** Strip the AI-writing tells: inflated pairings, throat-clearing openers, marketing adjectives, connective filler. Cut each hedge, or commit to the claim. Read every em dash and ask whether a period or a comma does the job.

**Flow.** Fix readability and the bridges between ideas. Does each paragraph follow from the one before? Does the reader ever rebuild a step you skipped? Split any sentence carrying two ideas.

**Accuracy.** Check every claim is supported. Check the register matches the audience from stage 1. Mark what you verified apart from what you inferred. Cut any number you cannot source.

Done when each pass has read the whole draft and its fixes are in.

### 7. Hand it back

Tell the user to read it aloud. That check is theirs, and nothing automates it. Once they approve, move the text to its surface: publish, create the doc, or copy it to its repo path.

## Corrections belong to the hooks

Leave the correction log and the rule files as they are while drafting. The user routes what promote surfaces.
