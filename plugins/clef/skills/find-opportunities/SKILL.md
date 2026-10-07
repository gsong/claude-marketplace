---
name: find-opportunities
description: "Find where Clef, Cloudflare's decision model, can make a system's repeated decisions. Surveys a repo, directory, file or prose, tests each decision point for fit, designs an experiment for each fit, and writes a record to clef-opportunities/. Use when the user asks where Clef fits or could help, wants to swap an LLM call, rule chain or manual triage step for Clef, or wants to resume a record in clef-opportunities/."
---

# Find Clef opportunities

Find the decision points in a system that Clef could make, run the fit test on each, design an experiment for each fit, and write it all to a record. The session ends with a review of that record.

This skill plans and writes only. It never runs `ollama` and never calls Clef, in any form. Clef first runs in an experiment's offline stage, long after this session ends.

Write "decision point" for one kind of item and its questions, never "candidate". Keep the record's terms: typed question, fit test, reject pattern, verdict, record, experiment, baseline, shadow mode.

## Files

- [fit-test.md](fit-test.md): decision points, typed questions, the readable properties F1–F5, the gates and every verdict. Read it before step 3.
- [reject-patterns.md](reject-patterns.md): R1–R11. Read it before step 3.
- [experiment-template.md](experiment-template.md): the shared experiment rules. Step 1 copies it into the record.
- [record-layout.md](record-layout.md): the record skeleton and the review rules. Read it before step 1.

## Asking

Ask the user one question at a time, each with a recommended answer. Use `AskUserQuestion` when it is available. Two rules govern every question:

1. If the user's messages already answer it, use that answer and do not ask.
2. If you cannot ask, for example because `AskUserQuestion` is unavailable in a `claude -p` run, record the answer as unknown. The review gathers it into the open items.

## Steps

### 1. Open the record

1. Name the record's path before any other work: `clef-opportunities/<input-name>-<date>.md` at the git root, or in the current directory outside a repo. `<input-name>` is the repo, directory or file name without its extension, or a short kebab-case name for prose. `<date>` is today as `YYYY-MM-DD`. The user may give another path.
2. If the input is an existing record, resume it: skip to step 3 at the first decision point marked "not reached".
3. Write the header, a Review section that reads "Review not run yet", and the Experiment template section, which holds the text of [experiment-template.md](experiment-template.md) verbatim. Follow [record-layout.md](record-layout.md).

Done when the file exists with those three parts.

### 2. Survey the whole input

1. Find every hit for the four signals:
   - **LLM call:** a model call whose reply is parsed into a label, enum, yes/no or score. The strongest signal.
   - **Rule chain:** if/elif chains, regexes or keyword lists that classify free text.
   - **Manual triage:** review queues, status fields, runbook steps, and verbs like triage, route, moderate, flag or prioritize in prose.
   - **Claude-side:** a hook, batch job or command where Claude decides about data it never reads in full.

   For a repo or directory, send four search subagents in parallel, one per signal. Each returns `file:line`, the kind of item, and a short note on the question asked there. For a file or prose, read it inline, with no subagents.

2. Group the hits by kind of item into decision points ([fit-test.md](fit-test.md#decision-points)).
3. Order the list. Product decision points come first, then Claude-side ones. Inside each group, order by signal: LLM call, rule chain, manual triage. Ties go to the higher volume the input shows.
4. Keep every hit. Each one reaches the record and ends with a verdict.
5. Show the list. The user may skip, reorder or add decision points. A skipped decision point gets "skipped by user" and the user's reason.
6. **Empty survey.** Ask one question: which items does the system handle again and again, and what does it decide about each? Named items join the list. If the user names none, write "Clef does not fit here" and what the survey searched, then go to step 5.
7. Write the Survey section. Then write a stub for every decision point that reads "Verdict: not reached". From here on, a session that stops leaves a valid record.

Done when the record holds the survey and one stub per decision point.

### 3. Work one decision point at a time

In list order, for each decision point:

1. Draft every typed question, with its recasts. Draft the F1–F5 and reject-pattern verdicts that the input shows. Show the draft in one block, and let the user correct it.
2. Ask, one at a time, only what the input cannot show: the unknown F1–F5 properties.
3. Run the fit-test gates in order ([fit-test.md](fit-test.md#gates)).
4. For a fit, including "fits, pending", design the experiment (see [Experiment](#experiment)).
5. Rewrite the stub as the full entry, with its verdict, as soon as the verdict is decided.

### 4. Stop

Stop when every decision point has a verdict, or when the user stops. Unworked decision points keep "not reached", so a later session can resume them.

### 5. Review

Run the four checks. Fix each failure in the record before you write the review.

1. Every decision point has a verdict.
2. Every fit has an experiment design, with a pass bar or "to set before the offline run".
3. Every unknown, pending latency measurement, open cloud check and unset pass bar is in the open items.
4. The fits are in planning order: local before cloud, then by stakes, then by volume.

Write the Review section by the review rules in [record-layout.md](record-layout.md#review-rules), and set the header's status. Let the user correct it. The review runs whether the session finished or stopped.

Leave the record uncommitted. The user decides what to do with it.

## Experiment

For each fit, fill the decision point's Experiment block from earlier answers:

- today's behavior per question (the F11 fallback)
- the strong LLM, such as Opus
- the labeled set and its top-ups
- the source of the labels (the F7 judge)
- who rechecks disputes
- the pass bar

Ask the user only for the pass bar. If the user is not ready, the bar reads "to set before the offline run". Each unknown value becomes an open item.
