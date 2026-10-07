# Fit test

## Decision points

A decision point is one kind of item, such as an email or a ticket. It holds every typed question a system asks about each item again and again at runtime. One item's facts fit in one Clef state.

**Priority.** Product decision points come first: decisions the system makes again and again at runtime, such as triage, routing or moderation. Claude-side decision points come second. A Claude-side decision point must name where its facts come from and show that those facts never enter Claude's context. Without that, every question in it gets R1.

## Typed questions

Write each question exactly as Clef receives it, as a YAML block keyed by question ID:

- `type`: `noul` (yes/no), `choice` (pick one) or `score` (rating on ordered levels).
- `instructions`: the full question, on every question.
- `criteria`: for a `choice`, every option ID with its description. For a `score`, every level's description as a list, lowest first. A `noul` may give `true` and `false` descriptions.

```yaml
ticket.team:
  type: choice
  instructions: Which team should handle this support ticket?
  criteria:
    auth: Login and account access
    billing: Payments, invoices and refunds
    none: None of these teams
ticket.urgency:
  type: score
  instructions: How soon does this ticket need an answer?
  criteria:
    - It can wait a week
    - It needs an answer this week
    - It needs an answer today
```

Rules:

- At most 26 `choice` options and 10 `score` levels, so one question works on both Ollama and Workers AI. Split a larger routing question into levels, such as team first and then queue.
- Every `score` level gets a description, never a bare number.
- "None of these" is an explicit option whenever it is a live answer. Clef has no abstain.
- **Question IDs are prompt text.** Ollama writes the ID into Clef's prompt. Make each ID read clearly, keep it identical on every host, and keep experiment arm labels out of it. IDs use only letters, digits, `_`, `.` and `-`, up to 100 characters.
- **State (R4).** The state holds only the item's facts. Rules go in the question instructions or stay in code.

**Recasts.** Record each recast next to its original question:

- "Which of these apply" becomes one `noul` per label. Clef has no multi-select.
- Open extraction becomes a `choice` among options that code already finds.
- A judged quantity, such as reach or effort, becomes a `score` with described bands. Recast it only when the system can act on the band and code cannot compute the number.

**Not typed:** free text, computed numbers, spans and lists. A question you cannot write as a typed question gets "not typed: <reason>".

## Readable properties

Each question must show these from the input:

- **F1:** the system asks it again and again at runtime.
- **F2:** Clef replaces a model call, or the facts never enter Claude's context.
- **F3:** it asks one fact about the item or a named part of it, never "find X inside it".
- **F4:** it can be written as a typed question.
- **F5:** code cannot decide it. Rules stay in code, and Clef gets the residue.

A question that fails one is dropped with that property as its verdict, such as "F1 fails: nothing acts on the answer".

When the input cannot show a property, ask the user. If the user does not know, or you cannot ask, mark it unknown. The question survives, and the unknown joins the verdict and the open items.

Also check R1, R2, R3, R7, R10 and R11 against each question ([reject-patterns.md](reject-patterns.md)). A match drops the question with the pattern as its verdict.

**Per-question filtering.** A decision point survives while at least one question passes. Record each dropped question, such as "Has an attachment? R11: a rule. Stays in code." If no question survives, the decision point gets "no fit: no question survived" with the patterns or properties that failed.

## Gates

Run the gates per decision point, in this order. The first three can fail outright, so they come first.

1. **F6 stakes.** Pass when a wrong answer costs little. With high stakes, pass only if Clef escalates, orders or pre-sorts, and a person or existing system keeps the final act. Fail under R6 if Clef would decide an irreversible act alone. Record the worst wrong answer and who catches it.
2. **F11 fallback.** Pass only when the fallback is today's behavior, such as the old model call, the rule chain or the manual queue.
3. **F7 judge.** Pass when the user names a source of true answers that is not Claude alone. Examples: past outcomes, existing human labels, or a person who will label a sample. The labels need not exist yet. Claude may draft labels for a person to check. When the user names none, list the sources that could serve as "possible judges".
4. **F10 latency.** Batch or background work passes. A request path records its budget in milliseconds and passes pending a latency measurement. Record whether the call site can call Clef at all.
5. **Where Clef runs.** Local is the default. Choose the cloud only when local Clef cannot run where the system runs, such as a server without a GPU or a machine without memory for the 11–18 GB model. Latency and volume never move a decision point to the cloud. A cloud choice records four fields:
   - why local Clef cannot run there
   - whether the data may leave the machine, and who said so. If it may not, the verdict is "no fit: cannot run locally and the data may not leave".
   - a cost estimate: volume × tokens per item × price per million input tokens, marked as an estimate. Workers AI charges $0.24 per million input tokens for `clef` and $0.09 for `clef-flash`.
   - the checks still open in the Cloudflare dashboard: rate limits, regions and image billing

**Failure and unknowns.** The first failed gate gives "no fit" and ends that decision point, with no experiment design. The entry lists the gates not asked. An unknown gate does not end the decision point. Record the unknown and go on through the remaining gates.

F8 (model choice) and F9 (threshold) are experiment settings, not gates.

## Verdicts

Each dropped question gets one of:

- "not typed: <reason>"
- a failed F1–F5 with its reason
- a reject pattern with its reason

Each decision point gets one of:

- **fits, local**
- **fits, cloud**
- **fits, pending <every unknown>**, such as "fits, pending the judge and a latency measurement". Name each unknown in plain words, with no F code: "the judge", never "the F7 judge" or "the judge (F7)". Every request-path fit carries "a latency measurement", because the skill never times Clef. The fit-test table still shows local or cloud.
- **no fit: <what failed>**: stakes (R6), no judge (F7), no fallback (F11), cannot run locally and the data may not leave, or no question survived.
- **skipped by user**, with the user's reason.
- **not reached**, left only when the session stops before it.

If no decision point fits, the record says "Clef does not fit here" and gives the reasons. That is a valid result.
