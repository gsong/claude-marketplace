---
name: ask
description: >-
  Ask Clef, a local decision model, a yes/no (noul),
  pick-one (choice) or rated (score) question about a text or JSON
  state and up to 4 images; each answer comes with a probability.
  Use for any decision that fits one of those question types when
  its facts fit in the state: classifying, triaging, checking a
  condition, choosing among options, rating against a rubric. Also
  use when the user names Clef, or to judge many items with the
  same questions in one batch run. Do not use when the answer is
  free text, a computed number or an extracted list, or when the
  judgment needs files, tools or history the state does not hold.
---

# Ask Clef

Call the script by its path, `${CLAUDE_PLUGIN_ROOT}/skills/ask/scripts/clef.py`, never through `uv run`, in one of two shapes, so it runs with no Bash prompt:

- `printf '%s' '<json>' | clef.py [flags]`. Keep the state's text exactly as given, and write each apostrophe in it as `'\''`.
- `clef.py [flags] < request.json`.

Give each flag value as a plain word or in single quotes. Any other shape asks the user first, and so does `--out`. `clef.py --help` lists every flag.

Stdin holds `state` (text or JSON) and `questions`. Images go in `--image PATH`, up to 4.

```sh
printf '%s' '{"state": "Oh fantastic, the app logged me out for the fifth time today.",
 "questions": {
   "complaint": {"type": "noul", "instructions": "Is this a complaint?"},
   "team": {"type": "choice", "instructions": "Which team handles it?",
     "criteria": {"auth": "Login and accounts", "billing": "Payments"}},
   "urgency": {"type": "score", "instructions": "How urgent is it?",
     "criteria": ["Can wait", "This week", "Today"]}}}' |
  ${CLAUDE_PLUGIN_ROOT}/skills/ask/scripts/clef.py --model clef-flash
```

Each `answers.<id>` in the reply holds the answer:

- `noul`: the probability of true.
- `choice`: the option id, with `probabilities`, one per option id.
- `score`: the expected level, where 0 is the first criterion, with `probabilities` keyed by level as a string (`"0"`, `"1"`, …).

`choice` and `score` also carry a `confidence`. It is one minus the entropy of `probabilities`, divided by the log of their count. It runs low even for a clear answer: a top option of two at 0.85 gets about 0.4. Judge an answer by its `probabilities`.

## When not to use Clef

- No question type fits: the answer is free text, a computed number or an extracted list.
- The judgment needs files, tools or history that the state does not hold.
- Clef's answer alone would trigger a hard-to-undo act, such as delete, send or deploy. Show the user the answers and your threshold first.

Otherwise, Clef's answer is the decision.

## Size guide

These limits keep a warm call under about 30 s. The script checks no length.

| Model        | State limit       |
| ------------ | ----------------- |
| `clef`       | 10,000 characters |
| `clef-flash` | 24,000 characters |

- Each image counts as 1,000 characters. Count with `wc -c`.
- Over `clef`'s limit but within `clef-flash`'s: use `clef-flash`.
- Over both: decide yourself, without Clef.
- The reply's `usage.input_tokens` lets you check afterward.

## Model choice

Use `clef-flash` when both models fit. If a key answer in a single call is close, you may re-ask that item on `clef`. An answer is close when its top probability is under 0.65. For a `noul`, that is a value between 0.35 and 0.65. For a `choice` or `score`, it is the highest `probabilities` value. Batches stay on `clef-flash`; re-ask only the close lines.

## Keeping tokens down

Clef saves your tokens only when the facts stay out of your context. Prefer `--state-file`, a batch, or images you have not viewed.

## Batch runs

A batch judges many items with the same questions. Build the batch file in one tool call. Then run `clef.py` alone in a second call, so the run gets no prompt.

1. **Build the batch file.** Each line holds `state` and `questions`, and may hold `id`, `images` (up to 4 paths) and `guess`. A batch takes no `--image`, `--state-file` or `--guess`. Write the file with one `jq` command, absolute paths and no `cd`. Put it in your scratchpad folder when your system prompt names one:

   ```sh
   jq -c '{state: .text, questions: {"complaint": {"type": "noul", "instructions": "Is this a complaint?"}}}
     + if has("id") then {id} else {} end' <dir>/tickets.jsonl > <scratchpad>/batch.jsonl
   ```

   Copy `id` only from items that have one, because a null `id` fails its line. This step may ask the user. `jq` keeps the items out of your context. For items already in your context, the Write tool works too.

2. **Run the batch.** The Bash command is the call alone:

   ```sh
   ${CLAUDE_PLUGIN_ROOT}/skills/ask/scripts/clef.py --batch <scratchpad>/batch.jsonl
   ```

   Add no `cd` or `&&` before it, no pipe or `> file` after it, and no `--out`. Each of those can make the call ask the user. Read the result lines from its output. When Claude Code saves a large output to a file, read that file with a plain `jq`, with no redirect.

A large batch can run past the Bash tool's 2-minute default. Raise the Bash timeout, or run the batch in the background.

## `--guess` and `CLEF_LOG`

- `--guess` records your own answers beside Clef's in the log. It changes nothing in the request.
- `CLEF_LOG`, when it names a file, gets one JSON line per answered call.

Neither is required.

## Exit codes

- **Batch output:** each answer line printed before the run stopped holds a good answer. With exit 2, only the lines with an `error` failed. If exit 2 printed no lines, the batch request itself is wrong.
- **Exit 2:** fix the request. If the server refused an over-long state, decide yourself. Stepping down to `clef-flash` does not help, because both models have the same window.
- **Exit 3:** tell the user once, with the stderr line and the fix from "Fixes for exit 3" in `${CLAUDE_PLUGIN_ROOT}/skills/ask/setup.md`. Then decide yourself for the rest of the session. Call Clef again only if the user says the server is back. Never start the server.

## Ollama

Reach Ollama only through the script. Never call Ollama's API or run `ollama` commands, except setup steps the user asks for.
