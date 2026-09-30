---
name: "discuss"
description: "Runs a multi-round dialogue between Claude and Codex and writes the outcome as a consensus document (consensus.md). Use when the user wants Claude and Codex to discuss a topic or reach consensus."
compatibility: "Requires the Codex CLI, reached through the codex:rescue runtime."
---

# Discuss with Codex

Run a multi-round, two-model dialogue between Claude (you) and Codex toward consensus on a topic the user provides.

You are an active participant, not a relay. You form your own position from the topic and project context, exchange views with Codex, update your stance based on its arguments, and aim to converge. Concede only when persuaded; a standing disagreement goes to the checkpoint as it is. Both sides must explicitly declare agreement for the discussion to conclude.

## Arguments

- **Topic** (optional positional): the discussion topic. If absent, ask via `AskUserQuestion`.
- `--rounds N` (optional flag): rounds per checkpoint. Default `3`. Min `1`, max `10`.

## Process

### Step 1: Gather parameters

Parse `--rounds` from the invocation if present. Otherwise default to `3`.

If no topic was provided, use `AskUserQuestion` with a free-form text field to ask for it. The question should mention the current working directory.

Then collect reasoning effort and sandbox mode as `${CLAUDE_PLUGIN_ROOT}/references/codex-prompting.md` describes. Default to `read-only`.

### Step 2: Build context and derive slug

Build the round 1 context block per `${CLAUDE_PLUGIN_ROOT}/references/codex-prompting.md`; the first prompt must be self-contained.

Derive `<slug>` from the topic: lowercase, kebab-case, alphanumerics and hyphens only, truncated to ≤40 chars. Example: topic `"Postgres vs DynamoDB for the events table"` → `postgres-vs-dynamodb-for-the-events-tab`.

**Resolve destination directory.** List existing subdirectories under `ai-swap/`. If one is a natural fit for this topic (e.g. an existing brainstorming folder for the same task — `ai-swap/add-user-auth/` when discussing OAuth vs JWT for add-user-auth), reuse it so the consensus sits alongside any prior `spec.md` / `plan.md`. Otherwise, fall back to a new `ai-swap/discuss-<slug>/` folder.

The output path will be `<resolved-dir>/consensus.md`.

### Step 3: Round 1 (fresh thread)

Internally form your initial position on the topic from the user's framing plus project context. Be concrete — pick a side, name tradeoffs.

Dispatch a fresh task through `Agent(subagent_type: "codex:codex-rescue")` as the reference describes, with `--model gpt-5.6-terra` as a CLI flag and `run_in_background: false` (need synchronous response).

Prompt template (round 1):

```
We're collaborating to reach consensus on: <TOPIC>

<CONTEXT BLOCK — external refs, prior decisions, constraints>

This is a multi-round dialogue between you (Codex) and me (Claude). Goal: reach consensus, not win. We're in the same project: <cwd>.

My position:
<Claude's initial take, with reasoning — 2-5 sentences>

Share your own position. End your response with EXACTLY one of these markers (case-sensitive, on its own line, last line of your response):

- `AGREED: <one-paragraph summary of the agreed position>`
- `DISAGREE: <one-paragraph summary of your counter-position>`

This is round 1.
```

Parse Codex's response: detect `AGREED:` or `DISAGREE:` on the last line. Set `codex_agrees` accordingly.

### Step 4: Round loop (rounds 2..N where N = rounds-per-checkpoint)

For each subsequent round:

1. Read Codex's last response.
2. Update your own position. Set `claude_agrees`:
   - `true` if Codex's argument is sound and you are persuaded
   - `false` if you still hold ground
3. If `claude_agrees && codex_agrees` → consensus reached, go to Step 6.
4. Otherwise, dispatch codex-rescue again with the `--resume` flag (continues the same Codex thread). No thread id is needed — the rescue runtime maps `--resume` to Codex's `--resume-last`, which picks up the most recent rescue thread in this repository:

```
Round <N>.

<Claude's updated position — explicitly address Codex's last point: what convinced you, what didn't, what's new>

End with `AGREED:` or `DISAGREE:` as before.
```

5. Parse the response, update `codex_agrees`. Repeat.

### Step 5: Checkpoint (after every N rounds without consensus)

**Round counting:** track total rounds across checkpoints. Hard cap at 15.

Use `AskUserQuestion` to present:

> Discussion checkpoint after round X. Claude: <agree|disagree>. Codex: <agree|disagree>. <one-line summary of where positions stand>. What next?

Options:

- **Continue** — run another N rounds
- **Redirect** — provide a steering note (free-form text via follow-up `AskUserQuestion`); prepend it to your next position before dispatching
- **Accept current state** — treat as user-accepted consensus (skip to Step 6, mark accordingly)
- **Abort** — end without writing consensus

If total rounds ≥ 9, warn the user before each remaining checkpoint that the hard cap is 15.

If total rounds reach 15 without consensus, force a "stuck" checkpoint: present only **Accept** or **Abort** (no Continue option).

### Step 6: Consensus output

Create the directory if needed: `mkdir -p <resolved-dir>/`.

Write `<resolved-dir>/consensus.md`:

```markdown
# Consensus: <topic>

Reached after <N> round(s) on <YYYY-MM-DD>.

**Status:** <Formal agreement | User-accepted at checkpoint, formal agreement not reached>

## Agreed position

<one-paragraph statement of the agreed position>

## Key reasoning

- <bullet 1>
- <bullet 2>
- <bullet 3-4 max>

## Tradeoffs noted

- <acknowledged downsides or open questions, if any>
```

Use the `utilities:date` skill for the date if it's not already known, or `date +%F` if that skill is unavailable.

Print to terminal: a one-paragraph summary of the consensus and the path to the file.

### Step 7: Aborted

If the user aborts at a checkpoint, do not write `consensus.md`. Print: `Discussion aborted at round <N>.`

## Error handling

- **Codex returns nothing or rescue fails:** present the error, ask via `AskUserQuestion` whether to retry the round, abort, or accept current state.
- **AGREED/DISAGREE marker missing or malformed:** re-dispatch once with an explicit format reminder appended. If a second attempt also fails to produce a parseable marker, present Codex's raw response to the user via `AskUserQuestion` and ask them to judge whether Codex agrees.
- **`--resume` fails (no thread found):** fall back to a fresh Agent call with a brief inline summary of prior rounds in the prompt. Print a warning so the user knows thread state was lost.
- **Round 1 fails outright:** abort with the codex-rescue stderr message. Suggest `/codex:setup` if Codex isn't installed.

## Notes

- Make a todo list at the start of a long discussion to track rounds and checkpoint cadence.
