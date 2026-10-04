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

The reply keys `answers` by question id. Each answer holds its value under a key named for its type:

```json
{
  "model": "clef-flash",
  "answers": {
    "complaint": { "type": "noul", "noul": 0.97 },
    "team": {
      "type": "choice",
      "choice": "auth",
      "probabilities": { "auth": 0.85, "billing": 0.15 },
      "confidence": 0.4
    },
    "urgency": {
      "type": "score",
      "score": 1.55,
      "probabilities": { "0": 0.13, "1": 0.18, "2": 0.69 },
      "confidence": 0.23
    }
  },
  "usage": { "input_tokens": 290, "output_tokens": 0 }
}
```

- `noul`: the probability of true. A `noul` that is missing, not a finite number, or exactly 0.5 is no answer. Re-ask it on `clef` as "Model choice" describes, or decide yourself.
- `choice`: the option id, with `probabilities`, one per option id.
- `score`: the expected level, a decimal where 0 is the first criterion. `probabilities` is keyed by level as a string (`"0"`, `"1"`, …). The most likely level is the top `probabilities` key, `"2"` in the example.

`confidence` runs low even for a clear answer. Judge an answer by its `probabilities`.

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

- Each image counts as 1,000 characters. Count characters with `wc -m`, not bytes with `wc -c`.
- Over `clef`'s limit but within `clef-flash`'s: use `clef-flash`.
- Over both: decide yourself, without Clef.
- The reply's `usage.input_tokens` lets you check afterward.

## Model choice

Use `clef-flash` when both models fit. If a key answer is close, you may re-ask that item on `clef` when its state fits `clef`'s limit. This holds for a single call and for a batch line. `clef`'s answer wins. If it is still close, decide yourself. An answer is close when its top probability is under 0.65. For a `noul`, that is a value between 0.35 and 0.65. For a `choice` or `score`, it is the highest `probabilities` value.

Batches stay on `clef-flash`. Re-ask only a batch's close lines on `clef`:

1. From the `clef-flash` run, collect the `id` or `line` value of each close result line.
2. Run the same batch file on `clef`, and list those values in `--ids`:

   ```sh
   ${CLAUDE_PLUGIN_ROOT}/skills/ask/scripts/clef.py --model clef --batch <scratchpad>/batch.jsonl --ids 'T3 T7 12'
   ```

`--ids` runs only the lines it lists. The re-ask writes no file, so it gets no prompt. It is a batch run, so the time limit and stop note in "Batch runs" apply to it too. Separate the values with spaces. A line with an `id` matches only by its `id`. A line with no `id`, or a bad one, matches by its line number. A value that is one line's `id` and another line's number runs both lines. For an `id` with a space or an apostrophe, use `--lines` with its line number. An `id` that starts with `-` makes the call ask the user.

## Keeping tokens down

Clef saves your tokens only when the facts stay out of your context. Prefer `--state-file`, a batch, or images you have not viewed. With `--state-file`, stdin holds only `questions`. A `state` in both places is exit 2.

## Batch runs

A batch judges many items with the same questions. Build the batch file in one tool call. Then run `clef.py` alone in a second call, so the run gets no prompt.

1. **Build the batch file.** Each line holds `state` and `questions`, and may hold `id`, `images` (up to 4 paths) and `guess`. A line's `guess` takes the same JSON object as `--guess`, as "`--guess` and `CLEF_LOG`" describes. A batch takes no `--image`, `--state-file` or `--guess`. Write the file with one `jq` command, absolute paths and no `cd`. Put it in your scratchpad folder when your system prompt names one:

   ```sh
   jq -c '{state: .text, questions: {"complaint": {"type": "noul", "instructions": "Is this a complaint?"}}}
     + if .id != null then {id} else {} end' <dir>/tickets.jsonl > <scratchpad>/batch.jsonl
   ```

   Copy `id` only when it is not null, because a null `id` fails its line. This step may ask the user. `jq` keeps the items out of your context. For items already in your context, the Write tool works too.

2. **Run the batch.** The Bash command is the call alone:

   ```sh
   ${CLAUDE_PLUGIN_ROOT}/skills/ask/scripts/clef.py --batch <scratchpad>/batch.jsonl
   ```

   Add no `cd` or `&&` before it, no pipe or `> file` after it, and no `--out`. Each of those can make the call ask the user. Read the result lines from its output. A result line is the reply plus the line's `id`, or `"line": N` for a line with no `id` or a bad one. A failed line names its line the same way, as in `{"id": "T3", "error": "clef: …", "exit": 2}`. Exit 0 does not mean every line succeeded. Find the failed lines as "Exit codes" describes. When Claude Code saves a large output to a file, read that file with a plain `jq`, with no redirect. To run only some lines, add `--ids` to pick them by `id`, as "Model choice" shows, or `--lines` to pick them by line number.

Run the whole batch file in one call, in the foreground, with the Bash tool's `timeout` set to 600000, its maximum. This is not `clef.py --timeout`, which limits each request. Never run a batch in the background: a `claude -p` session ends without waiting for it, and you lose its answers.

`clef.py` stops a batch before the Bash tool's limit. It starts no line that could end more than 570 s after the run began. When it stops early, it exits 0 and prints a stop note on stderr in place of the summary:

```text
clef: stopped at the time limit: 40 answered, 1 failed, 59 left; rerun with --lines '42-100'
```

1. Read the run's result lines.
2. Run the same batch file again, with the `--lines` value from the stop note, as a foreground call alone:

   ```sh
   ${CLAUDE_PLUGIN_ROOT}/skills/ask/scripts/clef.py --batch <scratchpad>/batch.jsonl --lines '42-100'
   ```

3. Repeat until a run prints no stop note.

Keep the same `--model` on each rerun. The stop note gives line numbers, even after an `--ids` run.

`--lines` picks a line by its number, even when the line has an `id`. It takes single numbers and ranges, as in `'1-50 75 90-100'`. A listed blank line runs nothing. If Claude Code moves a call to the background anyway, wait for its notification before you answer.

## `--guess` and `CLEF_LOG`

- `--guess` records your own answers beside Clef's in the log. It changes nothing in the request. Its value is a JSON object keyed by question id. Give `true` or `false` for a `noul` question, an option id for a `choice`, and a level index for a `score`, where 0 is the first criterion. For the first example's questions:

  ```sh
  --guess '{"complaint": true, "team": "auth", "urgency": 2}'
  ```

  Keep the single quotes, so the call gets no prompt. You may leave out any question. A guess that names no such question, or gives the wrong kind of answer, is exit 2.
- `CLEF_LOG`, when it names a file, gets one JSON line per call, answered or failed. A batch line is one call. A failed call's line holds `error` and `exit`.

Neither is required.

## Exit codes

- **Batch output:** a batch that reaches its last line exits 0, even when some lines failed. Find the failed lines by their `error` key. The stderr line `clef: N answered, M failed` gives the counts. A batch stopped at the time limit exits 0 too, and prints the stop note that "Batch runs" describes. Exit 3 or 1 stops a batch. Each answer line printed before the stop holds a good answer. A batch exits 2 only when the script refuses it before any line runs. It then prints no result lines.
- **Exit 2, or `"exit": 2` in a batch error line:** fix the request. If the server refused an over-long state, decide yourself. Stepping down to `clef-flash` does not help, because both models have the same window.
- **Exit 1:** the server failed, or the script hit an unexpected error. Tell the user the stderr line once. In a single call, decide yourself. A batch runs its lines in file order and stops at exit 1, so the lines with no result line are the ones after the last result line. Rerun them once with `--lines`. If that run exits 1 too, decide the rest yourself.
- **Exit 3:** tell the user once, with the stderr line and the fix from "Fixes for exit 3" in `${CLAUDE_PLUGIN_ROOT}/skills/ask/setup.md`. Then decide yourself for the rest of the session. Call Clef again only if the user says the server is back. Never start the server.

## Ollama

Reach Ollama only through the script. Never call Ollama's API or run `ollama` commands, except setup steps the user asks for.
