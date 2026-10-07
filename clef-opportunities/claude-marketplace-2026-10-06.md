# Clef opportunities: claude-marketplace

- **Input:** repo gsong/claude-marketplace at commit c952f85, all plugins under `plugins/`
- **File:** `clef-opportunities/claude-marketplace-2026-10-06.md`
- **Started:** 2026-10-06
- **Status:** complete. The review ran on 2026-10-06.
- **To resume:** run the skill on this file. It picks up at the first decision point marked "not reached".

## Review

One of 20 decision points fits: the logged draft correction in the writing plugin, run locally. The other 19 drop, most of them under one of three patterns. Under R1, Claude already reads the facts in context. Under R7, the question needs tools or history that one state cannot hold. Under R11, a rule in code decides it. No hook or script in the repo calls a model, so no decision point swaps out an existing model call.

### Verdicts

| #   | Decision point | Side | Signal | Verdict |
| --- | --- | --- | --- | --- |
| 1 | [PR review finding](#1-pr-review-finding) | product | LLM call | no fit: no question survived |
| 2 | [PR review comment from a reviewer](#2-pr-review-comment-from-a-reviewer) | product | LLM call | no fit: no question survived |
| 3 | [Pull request under review](#3-pull-request-under-review) | product | LLM call | no fit: no question survived |
| 4 | [docs-ai doc](#4-docs-ai-doc) | product | LLM call | no fit: no question survived |
| 5 | [Codex discussion reply](#5-codex-discussion-reply) | product | LLM call | no fit: no question survived |
| 6 | [Outgoing prose](#6-outgoing-prose) | product | rule chain | no fit: no question survived |
| 7 | [Logged draft correction](#7-logged-draft-correction) | product | rule chain | fits, local |
| 8 | [Published page text](#8-published-page-text) | product | rule chain | no fit: no question survived |
| 9 | [User prompt](#9-user-prompt) | product | rule chain | no fit: no question survived |
| 10 | [Bash tool call](#10-bash-tool-call) | product | rule chain | no fit: no question survived |
| 11 | [Findings JSON file](#11-findings-json-file) | product | rule chain | no fit: no question survived |
| 12 | [GitHub issue](#12-github-issue) | product | manual triage | no fit: no question survived |
| 13 | [Skill-scanner CI finding](#13-skill-scanner-ci-finding) | product | manual triage | no fit: no question survived |
| 14 | [Dependency upgrade](#14-dependency-upgrade) | product | manual triage | no fit: no question survived |
| 15 | [zizmor finding](#15-zizmor-finding) | product | manual triage | no fit: no question survived |
| 16 | [Project-board item](#16-project-board-item) | product | manual triage | no fit: no question survived |
| 17 | [CLAUDE.md instruction](#17-claudemd-instruction) | Claude | Claude-side | no fit: no question survived |
| 18 | [Uncommitted change](#18-uncommitted-change) | Claude | Claude-side | no fit: no question survived |
| 19 | [Headline option](#19-headline-option) | Claude | Claude-side | no fit: no question survived |
| 20 | [Clef decision point](#20-clef-decision-point) | Claude | Claude-side | no fit: no question survived |

### Fits, in planning order

Local before cloud, then by stakes, then by volume.

1. **Logged draft correction.** Local. Low stakes, about 4–5 corrections a week. Next: keep labeling new corrections until the set reaches 100, with top-ups for the small options. Then run the offline stage. The experiment is tracked in #151.

### Open items

- [ ] Logged draft correction: the labeled set holds 25 items and needs at least 100. At about 4–5 corrections a week, that takes about 16 more weeks.
- [ ] Logged draft correction: `voice` (3), `reference` (1) and `not_a_correction` (2) each have fewer than 10 items and need top-ups.

## Survey

**Searched:** every file under `plugins/` (skills, hooks, `bin/`, `scripts/`, references), plus `docs/`, `CONTEXT.md`, `README.md` and `.github/`. Four parallel search subagents ran, one per signal: LLM call, rule chain, manual triage and Claude-side. Eval fixtures under `plugins/clef/evals/` were excluded as test data. No hook or script in the repo calls a model. Every LLM call is a subagent or Codex call made by a skill that the user runs.

| Hit | Signal | Kind of item | Decision point |
| --- | --- | --- | --- |
| `plugins/gh-tools/skills/triage/SKILL.md:88-152` | LLM call | PR review finding | 1 |
| `plugins/gh-tools/skills/review/SKILL.md:115-229` | LLM call | PR review finding | 1 |
| `plugins/codex-tools/skills/review/SKILL.md:133-146` | rule chain | PR review finding | 1 |
| `plugins/gh-tools/skills/post-comments/SKILL.md:68-80` | rule chain | PR review finding | 1 |
| `plugins/gh-tools/skills/post-comments/SKILL.md:128-143` | manual triage | PR review finding | 1 |
| `plugins/gh-tools/skills/address-review/SKILL.md:44-112` | LLM call | PR review comment from a reviewer | 2 |
| `plugins/gh-tools/skills/review/SKILL.md:81-111` | LLM call | pull request under review | 3 |
| `plugins/codex-tools/skills/review/SKILL.md:86-107` | LLM call | pull request under review | 3 |
| `plugins/ai-docs/skills/check/SKILL.md:35-113` | LLM call | docs-ai doc | 4 |
| `plugins/ai-docs/skills/lookup/SKILL.md:30-58` | Claude-side | docs-ai doc | 4 |
| `plugins/ai-docs/skills/audit/SKILL.md:33-110` | LLM call | docs-ai doc | 4 |
| `plugins/ai-docs/skills/update/SKILL.md:57-100` | LLM call | docs-ai doc | 4 |
| `plugins/ai-docs/skills/init/SKILL.md:54-95` | LLM call | docs-ai doc | 4 |
| `plugins/codex-tools/skills/discuss/SKILL.md:59-139` | LLM call | Codex discussion reply | 5 |
| `plugins/writing/defaults/rules/{common,technical,comms,mixed}.md` | rule chain | outgoing prose | 6 |
| `plugins/writing/bin/voice-scan.pl:27-139` | rule chain | outgoing prose | 6 |
| `plugins/writing/hooks/gate.sh:36-159` | rule chain | outgoing prose | 6 |
| `plugins/writing/hooks/send-lint.py:44-104` | rule chain | outgoing prose | 6 |
| `plugins/writing/hooks/capture.sh:19-142` | Claude-side | logged draft correction | 7 |
| `plugins/writing/bin/promote.pl:12-110` | rule chain | logged draft correction | 7 |
| `plugins/writing/hooks/smart-quotes.py:44-168` | rule chain | published page text | 8 |
| `plugins/ai-docs/hooks/docs-reminder.sh:10-104` | rule chain | user prompt | 9 |
| `plugins/writing/hooks/send-lint.sh:15-20` | rule chain | Bash tool call | 10 |
| `plugins/writing/hooks/surfaces.py:184-260,469-482` | rule chain | Bash tool call | 10 |
| `plugins/gh-tools/scripts/validate-findings.py:68-142` | rule chain | findings JSON file | 11 |
| `docs/agents/triage-labels.md:1-14` | manual triage | GitHub issue | 12 |
| `docs/agents/issue-tracker.md:8-43` | manual triage | GitHub issue | 12 |
| `README.md:136-140` | manual triage | skill-scanner CI finding | 13 |
| `plugins/repo-maintenance/skills/gha/SKILL.md:32-85` | manual triage | dependency upgrade | 14 |
| `plugins/repo-maintenance/skills/pnpm-deps/SKILL.md:17-54` | manual triage | dependency upgrade | 14 |
| `plugins/repo-maintenance/skills/mise/SKILL.md:44` | manual triage | dependency upgrade | 14 |
| `plugins/repo-maintenance/skills/pnpm/SKILL.md:77` | Claude-side | dependency upgrade | 14 |
| `plugins/repo-maintenance/skills/zizmor/SKILL.md:24-48` | manual triage | zizmor finding | 15 |
| `plugins/gh-tools/skills/project-manager/SKILL.md:23-121` | manual triage | project-board item | 16 |
| `plugins/ai-memory/skills/review/SKILL.md:17-50` | Claude-side | CLAUDE.md instruction | 17 |
| `plugins/git-tools/skills/auto-squash/SKILL.md:30-80` | Claude-side | uncommitted change | 18 |
| `plugins/git-tools/skills/commit/SKILL.md:20` | Claude-side | uncommitted change | 18 |
| `plugins/writing/skills/draft/SKILL.md:50-60` | Claude-side | headline option | 19 |
| `plugins/clef/skills/find-opportunities/SKILL.md:40-50` | Claude-side | Clef decision point | 20 |

**User changes:** none. The user kept all 20 decision points in the order shown.

## Decision points

### 1. PR review finding

**Verdict: no fit: no question survived**

- **Where:** `plugins/gh-tools/skills/triage/SKILL.md:88-152`. One investigation agent per merged finding returns a verdict, an action and a suggested severity. Related hits: the merge step in `plugins/gh-tools/skills/review/SKILL.md:115-229`, the severity mapping in `plugins/codex-tools/skills/review/SKILL.md:133-146`, and the placement check and confirmation in `plugins/gh-tools/skills/post-comments/SKILL.md:68-143`.
- **Side:** product
- **Typed questions:**
  - `finding.verdict`, choice (valid, false_positive, already_addressed, pre_existing, unclear): Is this code review finding correct about the code as it stands now?
  - `finding.severity`, choice (must_fix, should_fix, nit): How serious is the problem this review finding describes?
  - `finding.body_clear`, noul: Does this comment body name its subject, stand alone, and leave out reviewer-process notes?
  - `findings.same_concern`, noul, on a pair of findings: Do these two review findings describe the same underlying problem?
- **`finding.verdict`:** R7. The agent reads the file, traces callers, runs `git log` and `git blame`, and searches tests. One state cannot hold that. `pre_existing` is also R11: a blame against the PR base decides it.
- **`finding.severity`:** F2 fails. The investigation call still runs for the verdict, so Clef adds a call and replaces none.
- **`finding.body_clear`:** F2 fails, for the same reason. The 80-word limit is R11: a word count stays in code.
- **`findings.same_concern`:** R1. Claude merges findings in triage Phase 1 after it reads every finding. The review synthesis merge is one part of a larger call that Clef would not replace.
- **Other hits:** the critical/high/medium/low severity mapping is R11, a lookup. Inline or review-body placement is R11, a hunk-range check. The user's confirmation in post-comments is R3.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 2. PR review comment from a reviewer

**Verdict: no fit: no question survived**

- **Where:** `plugins/gh-tools/skills/address-review/SKILL.md:10-112`. One agent per unanswered inline comment gives a verdict and a status against the code at the PR head.
- **Side:** product
- **Typed questions:**
  - `comment.verdict`, choice (fix, decline, wrong, decision): Against the code at the pull request head, how should the author respond to this review comment?
  - `comment.status`, noul: Does the evidence settle this verdict?
  - `comment.asks_beyond_inline`, noul: Does this review body ask for something that no inline comment on the pull request covers?
- **`comment.verdict`:** R7. The agent reads the code at the PR head and the linked issue, which one state cannot hold. The `decision` option is also R3: it asks whether the call is the user's.
- **`comment.status`:** F2 fails. The same agent produces it, so Clef replaces no call.
- **`comment.asks_beyond_inline`:** R1. Claude reads every review body and inline comment in Step 1.
- **Other hit:** stripping a leading `nit:` or `[must-fix]` label is R11, a regex.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 3. Pull request under review

**Verdict: no fit: no question survived**

- **Where:** `plugins/gh-tools/skills/review/SKILL.md:81-111`, where two reviewer agents read the PR. Also `plugins/codex-tools/skills/review/SKILL.md:86-146`, where three Codex runs each return findings and an `approve | needs-attention` verdict.
- **Side:** product
- **Typed questions:**
  - `pr.findings`: What problems does this pull request have? Not typed: a list of findings with spans and free text.
  - `pr.has_problem_in_area`, noul, one per focus area (recast of `pr.findings`): Does this pull request introduce a concurrency or state bug?
  - `pr.codex_verdict`, choice (approve, needs_attention): Should this pull request be approved as it stands?
- **`pr.has_problem_in_area`:** R2: it scans for a problem instead of confirming a named one. Also R7: the answer needs the repo beyond the diff.
- **`pr.codex_verdict`:** F2 fails. Codex returns it in the call that produces the findings, so Clef replaces no call.
- **Other hits:** the overall verdict (`needs-attention` if any agent says so) is R11. The merge on same file and overlapping lines is R11.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 4. docs-ai doc

**Verdict: no fit: no question survived**

- **Where:** `plugins/ai-docs/skills/check/SKILL.md:36-83`, where one Explore agent per doc returns a freshness rating. Related hits: the staleness flag in lookup, the reviewer agents in audit, and the analysts in update and init.
- **Side:** product
- **Typed questions:**
  - `doc.freshness`, choice (fresh, possibly_stale, likely_stale, unresolved): How current is this doc against the code it describes?
  - `doc.changes_matter`, noul: Do these changes to the doc's Key Paths since its baseline make anything the doc says untrue?
  - `doc.issues`: lists of accuracy issues, files to add, remove or merge, and new doc text. Not typed.
- **`doc.freshness`:** R11. The skill defines each rating as a rule: Key Paths resolve, 10 or more commits since the baseline, `file::Symbol` references exist. Glob, Grep and `git log` decide it. The agent does tool work only, so it is also R7.
- **`doc.changes_matter`:** F1 fails. No skill asks it today. The check counts commits and never judges the change.
- **`doc.issues`:** not typed. Audit's issue hunt is also R2, a scan.
- **Lookup's staleness flag:** R1, because Claude reads the doc itself. Also R11, because a commit count decides it.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 5. Codex discussion reply

**Verdict: no fit: no question survived**

- **Where:** `plugins/codex-tools/skills/discuss/SKILL.md:55-140`. Each round, Codex replies and ends with an `AGREED:` or `DISAGREE:` marker. Claude then decides whether it concedes. Up to 15 rounds per discussion, only when the user runs the skill.
- **Side:** product
- **Typed questions:**
  - `reply.codex_agrees`, noul: Does Codex agree with Claude's position in this reply?
  - `reply.claude_agrees`, noul: Is Codex's argument sound enough that Claude should concede?
  - `checkpoint.next`, choice (continue, redirect, accept, abort): What should the discussion do next?
- **`reply.codex_agrees`:** R11. A last-line check for the marker decides it.
- **`reply.claude_agrees`:** R1. Claude reads the reply in full and writes its next position from it.
- **`checkpoint.next`:** R3. The skill gives this choice to the user by design.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 6. Outgoing prose

**Verdict: no fit: no question survived**

- **Where:** `plugins/writing/hooks/gate.sh:36-159` runs after each Write or Edit of a draft or of repo markdown. `plugins/writing/hooks/send-lint.py:44-104` runs before each send to `gh`, Slack, Gmail, Claude Docs, Drive or Artifact. Both run `plugins/writing/bin/voice-scan.pl` with the rules in `plugins/writing/defaults/rules/*.md`.
- **Side:** product
- **Typed questions:**
  - `prose.<rule>`, one noul per Greppable rule, such as: Does this text use a semicolon?
  - `prose.has_preamble`, noul: Does this text open with a preamble before its point?
  - `prose.leads_with_outcome`, `prose.active_voice`, `prose.marks_confidence`, noul each, from the Judgment section that "the gate cannot check".
  - `send.bounce`, noul: Should this hard-surface send be denied once?
- **`prose.<rule>`:** R11. A regex, a word count or a density rate decides each one. They stay in code.
- **`prose.has_preamble` and the Judgment questions:** R1. Claude wrote the text in this session, and the `writing:draft` exit passes already judge these in context. Clef would add a call and replace none, so F2 fails too.
- **`send.bounce`:** R11. A rule on the surface and a state file decide it.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 7. Logged draft correction

**Verdict: fits, local**

- **Where:** `plugins/writing/hooks/capture.sh:19-142` logs each draft edit, with the user's instruction for that turn, to `~/.claude/state/writing-line/corrections.jsonl`. At each Stop, `plugins/writing/bin/promote.pl:12-110` groups the logged instructions by a shared stemmed word. When 3 turns share a word, it blocks the stop and asks the user to file the pattern as a voice rule, a reference entry or a discard.
- **Side:** product. **Volume:** 25 corrections from 2026-08-29 to 2026-10-06 (17 comms, 4 mixed, 4 technical), about 4–5 a week, counted from the log on 2026-10-06. Three patterns have surfaced: `option`, `pastedcontent` and `week`.
- **State:** the instruction (`reason`), the text before (`original`) and after (`rewrite`), each cut to 2000 characters, and the profile. No rules (R4).

#### Typed questions

```yaml
correction.kind:
  type: choice
  instructions: A user gave this instruction to change a draft. Given the text before and after the change, what kind of correction is it?
  criteria:
    voice: A change in how the text sounds that would apply to other drafts in this profile
    reference: A term, name or fact that holds beyond this draft
    content: A fix that applies to this draft only
    not_a_correction: The logged instruction does not ask for a change to the draft
```

The `not_a_correction` option was added on 2026-10-06, during the first labeling pass. Two of the 25 logged instructions ask for no change to the draft. One is a request about how Claude asks questions. In the other, the capture hook logged a task notification as the user's instruction. A "none of these" answer is live, so it is an explicit option.

**Recasts:** "Which corrections recur as one pattern?" becomes `correction.kind` on each correction. Only `voice` and `reference` corrections count toward a cluster, and `content` corrections never do. The keyword count in `promote.pl` stays in code.

**Properties:** F1 passes: every Stop reads the whole log. F2 passes: entries from earlier sessions never enter Claude's context, and Claude sees only a surfaced cluster. F3 and F4 pass. F5 passes: code uses a keyword proxy, and `promote.pl` says "the user is the classifier". The first labeling pass, on 2026-10-06, shows that all three surfaced patterns were noise. `pastedcontent` came from pasted-text tags in three comms instructions. `week` joined three content fixes. `option` joined three instructions about one draft's options, two of them content fixes. No reject pattern matches. The user still decides where each rule goes.

**Dropped:** none.

#### Fit test

| Gate | Result | Evidence |
| --- | --- | --- |
| F6 stakes | pass | Worst wrong answer: a real voice correction is marked `content`, so its pattern surfaces late or never. Nobody catches it, but it costs one missed rule. The reverse costs one extra question. The user keeps the final act. |
| F11 fallback | pass | Today every logged correction counts toward the keyword clusters. A log line with no kind keeps counting that way. |
| F7 judge | pass | The user labels the logged corrections. Claude drafts each label, and the user checks it. |
| F10 latency | pass | Background. `capture.sh` starts a detached call to Ollama on 127.0.0.1 and writes the kind next to the log line. Nothing waits on it. Bash or Perl can reach Clef there. |
| Where Clef runs | local | The user's Mac: Apple M4 Max, 64 GB, with `ollama` at `/opt/homebrew/bin/ollama`. |

#### Experiment

Fills the [experiment template](#experiment-template). Only this decision point's values appear here.

- **Today's behavior:** every correction counts toward a keyword cluster, as if each one were `voice` or `reference`.
- **Strong LLM:** Opus, same state and question text.
- **Labeled set:** the 25 logged corrections now. Their labels are in `~/.claude/state/writing-line/clef-labels.jsonl`, keyed by `prompt_id`. Claude drafted them, and the user checked all 25 on 2026-10-06 with no changes. The file sits beside the log and outside the repo, because the instructions quote private email. The split is 19 `content`, 3 `voice`, 1 `reference` and 2 `not_a_correction`. The set needs at least 100, and the log grows by about 4–5 a week, so about 16 more weeks. Top up any option with fewer than 10 items, and mark the top-ups.
- **Labels:** the user. A person checks every label.
- **Dispute recheck:** the user, blind.
- **Pass bar:** offline, Clef ties or beats today's behavior on the items it answers, with coverage of at least 70%. Shadow mode, the held-out sample stays within 5 points of the offline accuracy. Added on 2026-10-06, because today's behavior is right on only about 16% of corrections: in an offline replay of `promote.pl` over the labeled set, at least half of the patterns that surface with Clef's filter are ones the user would file as a rule or a reference.

### 8. Published page text

**Verdict: no fit: no question survived**

- **Where:** `plugins/writing/hooks/smart-quotes.py:44-168`. Before each publish to Artifact, a Slack canvas, Claude Docs or Drive, the hook denies text that has straight quotes.
- **Side:** product
- **Typed questions:**
  - `page.has_straight_quotes`, noul: Does the visible text contain a straight `'` or `"` outside code, tags and attributes?
- **`page.has_straight_quotes`:** R11. A fence toggle, regex stripping and an HTML parser decide it exactly. No judgment is left for Clef.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 9. User prompt

**Verdict: no fit: no question survived**

- **Where:** `plugins/ai-docs/hooks/docs-reminder.sh:10-104`. On the first qualifying prompt of a session, the hook injects a reminder to use `ai-docs:lookup`. If most docs are stubs, it asks for them to be filled in instead.
- **Side:** product
- **Typed questions:**
  - `prompt.skip`, noul: Is this prompt a slash command or under 10 characters?
  - `docs.mostly_stubs`, noul: Are at least 60% of the docs stubs?
  - `prompt.needs_docs`, noul: Would the project's AI docs help answer this prompt?
- **`prompt.skip`:** R11. A prefix and a length check decide it.
- **`docs.mostly_stubs`:** R11. A grep for `<!-- NEEDS CONTENT` decides it.
- **`prompt.needs_docs`:** F1 fails. The hook never asks it and fires once per session on any prompt. It is also R1, because Claude reads the prompt in full.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 10. Bash tool call

**Verdict: no fit: no question survived**

- **Where:** `plugins/writing/hooks/send-lint.sh:15-20` drops any Bash call that never mentions `gh`. `plugins/writing/hooks/surfaces.py:184-260,469-482` then decides whether the command posts text to GitHub, and finds its body.
- **Side:** product
- **Typed questions:**
  - `command.mentions_gh`, noul: Does this command mention `gh`?
  - `command.is_send`, noul: Does this command post text to GitHub?
  - `command.body`: the body text. Not typed: a span.
- **`command.mentions_gh`:** R11. One regex decides it.
- **`command.is_send`:** R11. Shell tokens, a verb set, and heredoc and flag parsing decide it.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 11. Findings JSON file

**Verdict: no fit: no question survived**

- **Where:** `plugins/gh-tools/scripts/validate-findings.py:68-142`. Triage runs it on each findings file before and after it works.
- **Side:** product
- **Typed questions:**
  - `finding.valid_shape`, noul: Does this finding match the schema (severity values, `start_line` at or below `line`, side values, `input_sources` on triage output)?
- **`finding.valid_shape`:** R11. A schema and comparisons decide it exactly. The script never reads a finding's meaning.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 12. GitHub issue

**Verdict: no fit: no question survived**

- **Where:** `docs/agents/triage-labels.md:1-14` and `docs/agents/issue-tracker.md:8-43`. Claude runs the mattpocock-skills triage skill on each issue and applies one of the five triage labels. Volume: 67 issues from 2026-03-30 to 2026-10-07, about 2.5 a week. Labels on 2026-10-06: `ready-for-agent` 21, `ready-for-human` 7, `wontfix` 4, `needs-triage` 2.
- **Side:** product
- **Typed questions:**
  - `issue.triage_role`, choice (needs_info, ready_for_agent, ready_for_human): Which triage state fits this GitHub issue as written?
  - The `wontfix` option was dropped under R3. Whether to act on an issue is the user's intent.
- **`issue.triage_role`:** R1. The user said on 2026-10-06 that Claude runs `/triage` on each issue. Claude reads the issue in full there, so Clef would add a call and replace none.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 13. Skill-scanner CI finding

**Verdict: no fit: no question survived**

- **Where:** `README.md:136-140` and `.github/workflows/skill-scan.yml:34`. A person decides whether each Cisco skill-scanner finding is a real risk to fix, a false positive to suppress, or a rule to disable. Volume: only when a skill change trips a rule. This is inferred, because the repo holds no count.
- **Side:** product
- **Typed questions:**
  - `finding.triage`, choice (real_risk, false_positive, never_applies): Is this scanner finding a real risk in this skill?
- **`finding.triage`:** R7. Telling a real risk from a false positive needs the skill's other files and its purpose, not only the matched text. F1 is weak too, because the question comes up rarely. Had it survived, F6 would need a person to keep the act: a wrong `false_positive` suppresses a real security risk.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 14. Dependency upgrade

**Verdict: no fit: no question survived**

- **Where:** `plugins/repo-maintenance/skills/gha/SKILL.md:32-85`, `plugins/repo-maintenance/skills/pnpm-deps/SKILL.md:17-54`, `plugins/repo-maintenance/skills/mise/SKILL.md:44` and `plugins/repo-maintenance/skills/pnpm/SKILL.md:77`. Each skill lists outdated dependencies, holds back the ones inside the cool-down, looks up breaking changes and asks the user before applying.
- **Side:** product
- **Typed questions:**
  - `upgrade.in_cooldown`, noul: Was this release published less than N days ago?
  - `upgrade.bump_kind`, choice (major, minor, patch): What kind of version bump is this?
  - `upgrade.breaking`, noul: Does this release break anything this repo uses?
  - `upgrade.apply`, noul: Should these updates be applied?
  - `pnpm.is_version_ref`, noul: Is this grep match a pnpm version reference?
- **`upgrade.in_cooldown`:** R11. A date comparison decides it.
- **`upgrade.bump_kind`:** R11. A semver comparison decides it.
- **`upgrade.breaking`:** R7. It needs a changelog found on the web and the repo's own usage, which one state cannot hold. Claude does this research in context, so it is R1 as well.
- **`upgrade.apply`:** R3. The user confirms by design.
- **`pnpm.is_version_ref`:** R1. Claude reads each match itself.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 15. zizmor finding

**Verdict: no fit: no question survived**

- **Where:** `plugins/repo-maintenance/skills/zizmor/SKILL.md:24-48`. The skill groups zizmor findings on the GitHub Actions workflows and asks the user to approve each fix. One run covers `.github/workflows/`, which holds 2 workflows here.
- **Side:** product
- **Typed questions:**
  - `finding.severity`, choice: How severe is this finding? zizmor reports it.
  - `finding.fix_approved`, noul: Should this finding be fixed?
  - `finding.real_issue`, noul: Is this finding a real issue in this workflow?
- **`finding.severity`:** R11. zizmor's output gives it, and code groups by type, severity and file.
- **`finding.fix_approved`:** R3. The user approves each fix by design.
- **`finding.real_issue`:** R1. Claude reads the workflow and the audit docs in context. Also R10: zizmor's audit logic is third-party code.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 16. Project-board item

**Verdict: no fit: no question survived**

- **Where:** `plugins/gh-tools/skills/project-manager/SKILL.md:23-121`. The skill writes an agent that maps the user's words for a status to a Status column on the project board, then moves the item. It runs only when the user asks to move an item.
- **Side:** product
- **Typed questions:**
  - `request.target_status`, choice (the board's Status options): Which Status column does this request name?
- **`request.target_status`:** R3. The status the user wants is the user's intent, stated in their own words. It is also R1, because the agent reads the request in full. In the usual case a lowercase name lookup decides it (R11).
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 17. CLAUDE.md instruction

**Verdict: no fit: no question survived**

- **Where:** `plugins/ai-memory/skills/review/SKILL.md:17-50`. Claude sorts every instruction in one CLAUDE.md into keep, condense or remove, and scores the file from 1 to 10.
- **Side:** Claude
- **Typed questions:**
  - `instruction.action`, choice (keep, condense, remove): Does this instruction earn its tokens?
  - `file.effectiveness`, score (10 levels): How effective is this CLAUDE.md as a whole?
- **`instruction.action`:** R1. Claude reads the whole CLAUDE.md to judge it, and the file loads into every session anyway. The `remove` option is also R3: dropping the user's own instruction is the user's call.
- **`file.effectiveness`:** R1, for the same reason.
- **Claude-side check:** the facts enter Claude's context, so every question gets R1.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 18. Uncommitted change

**Verdict: no fit: no question survived**

- **Where:** `plugins/git-tools/skills/auto-squash/SKILL.md:30-80` matches each changed file to the branch commit it fixes. `plugins/git-tools/skills/commit/SKILL.md:20` groups hunks into commits and picks a type.
- **Side:** Claude
- **Typed questions:**
  - `change.fixup_target`, choice (the branch's commit SHAs, plus none): Which branch commit does this change belong to?
  - `change.commit_type`, choice (feat, fix, docs, refactor, test, chore): What type of commit is this change?
  - `change.group`: which hunks go together. Not typed: a partition of a list.
- **`change.fixup_target`:** R1. Claude reads the diff and `git log` for each file in context. Also R7: it needs the branch history, not only the change.
- **`change.commit_type`:** R1. Claude groups the hunks and writes the message in the same pass.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 19. Headline option

**Verdict: no fit: no question survived**

- **Where:** `plugins/writing/skills/draft/SKILL.md:50-64`. For a long draft in the mixed profile, Claude writes three headline and subhead options and scores each against three criteria. The user picks one.
- **Side:** Claude
- **Typed questions:**
  - `headline.score`, score, one per criterion from the skill: How well does this headline meet the criterion?
- **`headline.score`:** R1. Claude wrote the three options in this session and scores them in the same pass. The user picks the headline (R3), so the score only orders the options.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

### 20. Clef decision point

**Verdict: no fit: no question survived**

- **Where:** `plugins/clef/skills/find-opportunities/SKILL.md:40-50`. This skill surveys an input, judges each question's properties and gives each decision point a verdict. It makes one record per survey.
- **Side:** Claude
- **Typed questions:**
  - `property.passes`, one noul per F1–F5 property: Does this question have the property?
  - `decision_point.verdict`, choice: Which verdict does this decision point get?
  - `survey.hits`: lists of `file:line` and notes from the search subagents. Not typed.
- **`property.passes`:** R1. Claude reads the code and the survey hits in context to judge them. Also R7: it needs the code around each hit.
- **`decision_point.verdict`:** R3 in part. The user corrects every draft and answers the gate questions.
- **`survey.hits`:** not typed. The search is also R2, a scan.
- **Gates not asked:** F6 stakes, F11 fallback, F7 judge, F10 latency, where Clef runs.

## Experiment template

These rules hold for every experiment in this record. Each decision point's Experiment block gives only its own values.

- **Unit.** One experiment per decision point that fits. One labeled set, with a label on each item for each surviving question. Each question gets its own metrics, threshold and pass or fail.
- **Baselines.** Clef and both baselines run on the same items. Today's behavior is the fallback. A strong LLM is a reference ceiling only. It gets the same state and question text and must return one of the same options. When today's behavior is a person working a manual queue, the person's decisions are often the labels too. Then report agreement with the person and time saved.
- **Labeled set.** At least 100 items, at random from real recent items. Top up any option or level with fewer than 10 items, and mark the top-ups. The F7 source labels them. Claude may draft labels, but a person checks every one.
- **Stages.** Each stage must pass before the next starts. The user may stop after any stage.
  1. Offline: `clef`, `clef-flash` and both baselines run on the labeled set.
  2. Shadow mode: Clef answers at the real call site but only logs. A fresh labeled sample of the log is the held-out test. This stage also measures latency under real load.
  3. Act: Clef's answer takes effect above the threshold.
- **Metrics,** per question, for Clef and both baselines:
  - accuracy against the labels; for `score`, also the mean distance in levels
  - accuracy by Clef's top probability: below 0.65, 0.65–0.8, 0.8–0.9, 0.9 and up
  - coverage at the threshold (the share of items Clef answers), and accuracy on those items
  - the measured tokens and money of the call Clef replaces (R9); for the cloud, add the Workers AI price
  - median and 95th-percentile latency per item, on the target machine
- **Threshold (F9).** Per question: the lowest top probability where Clef ties or beats the fallback on the items it answers. Gate on `probabilities`, never on `confidence` or the margin (R8).
- **Pass bar.** Written into the record before any run. Offline: Clef ties or beats the fallback on the items it answers, and coverage meets a minimum the user sets. Manual queue: agreement with the person meets a minimum set in advance. Shadow mode: the held-out sample stays within 5 points of the offline accuracy. The strong LLM is not part of the bar.
- **Disputes.** The labels are the truth. One case gets a recheck: Clef and the strong LLM agree, but not with the label. The F7 labeler checks that item again, blind to which system said what. The record lists every changed label and shows results before and after. Claude never decides a dispute (R5).
- **Model (F8).** `clef-flash` wins when it passes on every question, since it is smaller and faster. Otherwise `clef` wins. Keep both results.
- **Latency.** Offline measures both models on the target machine against the budget in the record. A pass turns "pending a latency measurement" into "fits, local". An over-budget result is a flag, not a "no fit". The user decides at the act stage whether it matters. Latency never moves a decision point to the cloud.
- **Stability.** Offline also runs each question alone. If that changes more than 5% of a question's answers, mark the question unstable.
- **Option order.** No local check: Ollama sorts `choice` options by option ID, so the experiment and production see the same order. A cloud fit runs one check: the same request with the options in two orders, compared by probabilities. Reordering keys does nothing on Ollama, so rename option IDs to change the order. More than 5% changed answers marks the question unstable.
- **Multi-label recasts.** Label full label sets, and report the exact-set match rate.
- **Act stage.** Above the threshold, Clef's answer replaces the fallback. Below it, the fallback runs as today. The fallback stays wired in, so going back is one switch. A person labels a small sample of acted items, such as 20 a month. A drop below the bar switches back. An unstable question cannot reach the act stage until it is rewritten and passes again.
- **Setup sources.** Running Clef locally takes these:
  - [Ollama's Clef page](https://ollama.com/library/clef)
  - [Cloudflare's Clef docs](https://developers.cloudflare.com/workers-ai/models/clef/)
  - the [old setup guide](https://github.com/gsong/claude-marketplace/blob/6abcd57a36bb3d122258d0a4c183600c2c3bd968/plugins/clef/skills/ask/setup.md), for facts published nowhere else: pin the builds with `ollama cp`, never `ollama pull clef`; keep Ollama on 127.0.0.1; plan for about 36 GB of memory
