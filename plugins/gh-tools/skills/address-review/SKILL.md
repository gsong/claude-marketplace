---
name: "address-review"
description: "Validate, fix or decline, and reply to each review comment others left on your own GitHub PR."
disable-model-invocation: true
compatibility: "Requires the gh CLI (authenticated) and push access to the PR branch."
argument-hint: "<pr-number>"
---

# Address Review

Work through the review comments on PR #$ARGUMENTS until every comment has one reply that states its outcome. The user wrote the PR; the comments come from its reviewers.

## Step 1: Collect

Work on the PR's head branch. If the working tree is dirty, or the branch is behind its remote, stop and tell the user.

Fetch the PR, its comments and its reviews. Leave out `diff_hunk`: it floods the context, and the file at the head is what matters.

```bash
gh pr view $ARGUMENTS --json number,title,body,headRefName,headRefOid,closingIssuesReferences
gh api --paginate repos/{owner}/{repo}/pulls/$ARGUMENTS/comments \
  --jq '.[] | {id, path, line, user: .user.login, in_reply_to_id, body}'
gh api --paginate repos/{owner}/{repo}/pulls/$ARGUMENTS/reviews \
  --jq '.[] | {id, user: .user.login, state, body}'
gh api --paginate repos/{owner}/{repo}/issues/$ARGUMENTS/comments \
  --jq '.[] | {id, user: .user.login, body}'
```

Read each linked issue with `gh issue view <n> --json title,body,comments`. It is the spec that a scope or spec comment cites.

The **work list** holds each inline comment that opens a thread (`in_reply_to_id` is null) and has no reply yet from you (`gh api user --jq .login`). Add an issue comment or a review body only when it asks for something no inline comment covers. A review body usually summarizes the inline comments, so read it for how the reviewer groups them.

Done when the work list names each comment's id, its `path:line`, and its claim in one line.

## Step 2: Validate

Give each comment a **verdict** against the code at the PR head:

- **fix**: the claim holds, and the fix is clear.
- **decline**: the claim holds in part, or the fix costs more than it buys.
- **wrong**: the claim does not hold.
- **decision**: the claim holds, and the response is the user's call. It changes the spec or the scope, or it reverses a tradeoff the PR chose on purpose.

A subagent gives each verdict, so it comes from an independent reading of the code. You settle the results and then apply them.

### Investigate

Spawn one subagent per work-list comment, `subagent_type: general-purpose`. Launch at most 15 per message, and wait for each batch to return before the next. A session runs at most 20 subagents at once, and a spawn past that fails. Each subagent starts with a clean context, so its prompt carries every value below, spelled out. A shell variable never crosses into a subagent.

Strip a leading label such as "nit:" or "[must-fix]" from the body you pass, so the subagent judges the claim alone.

Each subagent receives this prompt:

---

You are investigating one review comment on PR #{number}. Give a verdict that rests on evidence from the code at the PR head.

**Comment {id}** at `{path}:{line}`:

{body, label stripped}

**PR head:** {headRefOid}, checked out in the working tree.
**PR title:** {title}
**PR body:** {PR body}
**Linked issues:** {each issue's title and full body, or "none"}

**Verdicts:** {the four verdict definitions above, copied as written}

Other investigators share this working tree, so treat it as read-only. Read files, and run commands that write nothing inside the tree. To try an edit, copy the files to a directory from `mktemp -d` and work there. Return any check that must edit the tree or run the test suite in `proposed_checks`. The orchestrator runs those checks one at a time. Post nothing to GitHub.

Check a claim about behavior by running it: plant the violation in a scratch copy, or pipe in a sample input. Hand a claim about a tool's documented behavior to a subagent that quotes the doc, for example `claude-code-guide` for Claude Code.

Before you give `decision`, read the PR body and the linked issues. When one of them states the intent the comment touches, give `fix` or `decline` instead, and quote that text as evidence.

Set `status` to `unclear` when one of these holds, and name it in `reason`:

- The verdict rests on a claim you could not verify.
- The evidence fits two verdicts.
- The fix has two forms that behave differently.
- The verdict is `decision`.

Otherwise set `status` to `clear`. A claim that a proposed check settles counts as verified.

Return only this JSON object, with no code fence:

{"comment_id": {id}, "verdict": "fix | decline | wrong | decision", "status": "clear | unclear", "reason": "why unclear, or null", "evidence": [{"what": "the command run, file read, or doc quoted", "result": "its output or the quoted text"}], "proposed_fix": "the files and the change, or null", "proposed_checks": [{"edit": "the change to make in the tree", "command": "the command to run", "expected": "the output that confirms the verdict"}], "unverified": ["each claim the verdict rests on that you could not check"]}

Done when each claim in the comment has evidence or appears in `unverified`.

---

### Settle

After the last batch returns, parse each result.

1. Run each proposed check, one at a time. Make the edit, run the command, and compare its output with `expected`. Restore the files with `git restore`, and confirm that `git status` is clean before the next check.
2. Mark a comment **unclear** when any of these holds:
   - its result says `unclear`
   - its subagent failed, or returned output that does not parse
   - its evidence cites no command, output or quote
   - a proposed check failed, or its output did not match `expected`
3. Read the results together. Group the comments whose proposed fixes make the same change; the group gets one fix, and each reply cites its SHA. The review body often says which comments belong together. Two fixes that edit the same lines differently, or where one undoes the other, are a **conflict**. Mark both comments unclear.

Print one line per comment: its id, `path:line`, verdict, and status. Go on without waiting for the user.

Done when each work-list comment has a verdict and a status, and each clear verdict has the evidence behind it.

## Step 3: Ask

Put every unclear comment to the user with AskUserQuestion, up to four questions per call. A conflict pair shares one question. Each question names the comments it settles, gives the subagent's `reason`, and says in one sentence what is at stake. Put your recommendation first, marked "(Recommended)". Offer the lightest option the reviewer gave, such as "record the change on the issue", beside "change the code".

A clear verdict stands as the subagent gave it. With nothing unclear, go to Step 4.

## Step 4: Apply

Make the fixes and the options the user chose. Follow the repo's own instructions for each file you touch. Update every place that restates what you changed: docs, code comments, the PR body.

Verify each change against the evidence behind its verdict. The planted violation now fails, the sample input gives the right result, and the full test and lint suites pass.

Commit in logical groups, in the repo's commit convention, so each reply can cite a SHA. Push the branch before you reply, because the replies cite the commits.

Record each decision where its readers look:

- The linked issue's plan no longer holds: edit the issue body so it states the plan as it now is.
- The user keeps scope beyond the issue: post one comment on the issue that lists each addition and why it is there.
- A fix made a line of the PR body untrue: edit that line.

Done when each fix and each chosen option is committed, pushed and verified, and the issue and the PR body match the code.

## Step 5: Reply

If the `writing:draft` skill is available, gate the replies first. Read `${CLAUDE_PLUGIN_ROOT}/references/voice-gate.md` and follow it, writing the bodies to `ai-swap/drafts/technical/pr-$ARGUMENTS-replies.md`.

Reply once to each work-list comment, in its thread:

```bash
gh api -X POST repos/{owner}/{repo}/pulls/$ARGUMENTS/comments/{id}/replies -f body='...'
```

Answer a work-list issue comment or review body with one `gh pr comment $ARGUMENTS`, and quote the line you answer.

Each reply is **terse**: the outcome first, then at most two short sentences of reason. Keep it under 50 words. The commit and the diff carry the detail, so the reply names what changed and stops.

- `Fixed in {sha}. {what changed}.`
- `Kept. Recorded on #{issue}: {link}.`
- `Declined. {why}.`
- `Not changed: {the evidence that the claim does not hold}.`

Start at the outcome word. Restating the comment, thanking the reviewer and softening the answer all add length and say nothing. Name anything you did not verify, in one clause. Leave each thread open for the reviewer to resolve.

Two replies at the right length:

> Fixed in bb0f42f. With no ESLint, the hook now returns `decision: "block"` and says to run `mise install`.

> Kept. The pnpm move stays in this PR, so this line stays too.

Done when a fresh fetch of the comments shows exactly one new reply from you on each work-list comment, and each reply is under 50 words.

## Step 6: Report

Tell the user, briefly:

- what you fixed, as `file:line`
- what you recorded, and where
- what you declined, and why
- what stays unverified
- the CI status of the pushed head
