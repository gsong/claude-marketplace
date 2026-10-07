# Record layout

The record is one Markdown file. Its sections come in this order: header, Review, Survey, Decision points, Experiment template. `<angle brackets>` mark values you fill. Keep every section heading even while its section is empty, so a stopped session still leaves a valid record.

Each decision point entry takes one of the four shapes below: a fit, a no-fit, a skip, or one not reached. A fit with "fits, pending" uses the fit shape. Leave out the Cloud block unless the fit runs in the cloud.

````markdown
# Clef opportunities: <input-name>

- **Input:** <repo at commit | directory | file | prose>
- **File:** `clef-opportunities/<input-name>-<date>.md`
- **Started:** <date>
- **Status:** <in progress | stopped | complete. The review ran on <date>.>
- **To resume:** run the skill on this file. It picks up at the first decision point marked "not reached".

## Review

<"Review not run yet" until the review runs.>

### Verdicts

| #   | Decision point      | Side             | Signal                                              | Verdict   |
| --- | ------------------- | ---------------- | --------------------------------------------------- | --------- |
| 1   | [<name>](#<anchor>) | product / Claude | LLM call / rule chain / manual triage / Claude-side | <verdict> |

### Fits, in planning order

Local before cloud, then by stakes, then by volume.

1. **<decision point>.** <Local | Cloud>. <stakes>, <volume>. Next: <next step>.

### Open items

- [ ] <decision point>: <unknown, pending latency measurement, open cloud check, or unset pass bar>

## Survey

**Searched:** <what was searched, and how>

| Hit           | Signal   | Kind of item | Decision point |
| ------------- | -------- | ------------ | -------------- |
| `<file:line>` | <signal> | <kind>       | <#>            |

**User changes:** <skips, reorders, additions, or "none">

## Decision points

### 1. <name>

**Verdict: <verdict>**

- **Where:** `<file:line>` and what happens there.
- **Side:** <product | Claude>. **Volume:** <volume and its source, or unknown>.
- **State:** <the item's facts>. No rules (R4).

#### Typed questions

```yaml
<question.id>:
  type: <noul | choice | score>
  instructions: <the full question>
  criteria:
    <option_id>: <description>
```

**Recasts:** <each recast, beside its original question>

**Dropped:**

| Question   | Verdict           |
| ---------- | ----------------- |
| <question> | <verdict: reason> |

#### Fit test

| Gate            | Result                     | Evidence                                                                        |
| --------------- | -------------------------- | ------------------------------------------------------------------------------- |
| F6 stakes       | <pass / fail / unknown>    | Worst wrong answer: <…>. <who catches it>.                                      |
| F11 fallback    | <…>                        | <…>                                                                             |
| F7 judge        | <…>                        | <…>                                                                             |
| F10 latency     | <pass / pending / unknown> | <batch, or request path with budget in ms; whether the call site can call Clef> |
| Where Clef runs | <local / cloud>            | <hardware>                                                                      |

<Cloud fits only:>

**Cloud:**

- **Why not local:** <…>
- **Data may leave the machine:** <yes, said by <who> on <date>>
- **Cost estimate:** <volume × tokens per item × price per million, marked estimate>
- **Open checks in the Cloudflare dashboard:** rate limits, regions, image billing.

#### Experiment

Fills the [experiment template](#experiment-template). Only this decision point's values appear here.

- **Today's behavior:** <per question>
- **Strong LLM:** <model>, same state and question text.
- **Labeled set:** <at least 100 items, source, top-ups>
- **Labels:** <F7 source>. A person checks every label.
- **Dispute recheck:** <who>, blind.
- **Pass bar:** <bar, or "to set before the offline run">

### 2. <name of a no-fit decision point>

**Verdict: no fit: <what failed>**

- **Where:** `<file:line>`. <what happens there>
- **Side:** <product | Claude>
- **Typed questions:** <one line each: ID, type, question>
- **<Failed gate or property>:** fail. <reason>
- **Gates not asked:** <list>

### 3. <name of a skipped decision point>

**Verdict: skipped by user**

- **Reason:** "<the user's words>"

### 4. <name of an unworked decision point>

**Verdict: not reached**

## Experiment template

<the shared rules from experiment-template.md, verbatim>
````

## Review rules

- The review is written last but placed first, so a planning session reads it first.
- The verdicts table has one row per decision point, each linking to its entry.
- Each fit gets one line in planning order, with its next step.
- Each open item names its decision point. A request-path fit's latency item points to the setup sources in the experiment template.
- The review does not list the four checks. Fix a failing check before you write the review.
- If nothing fits, the review opens with "Clef does not fit here" and the reasons, and has no fits or open items. The reasons include what the survey searched.
