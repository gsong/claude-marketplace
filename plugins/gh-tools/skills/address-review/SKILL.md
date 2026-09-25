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

The reviewer's label (fix, suggestion, nit, must-fix) is input to the verdict, not the verdict.

Read the cited file and line yourself. Check a claim about behavior by running it: plant the violation in a scratch copy, pipe in a sample input, run the suite. Hand a claim about a tool's documented behavior to a subagent that quotes the doc, for example `claude-code-guide` for Claude Code. Launch independent checks in parallel.

Group the comments that one change or one decision settles. The review body often says which.

Done when each work-list comment has a verdict, and each fix, decline and wrong verdict has the evidence behind it.

## Step 3: Ask

Put every decision to the user with AskUserQuestion, up to four questions per call. Each question names the comments it settles and says in one sentence what is at stake. Put your recommendation first, marked "(Recommended)". Offer the lightest option the reviewer gave, such as "record the change on the issue", beside "change the code".

Ask too when a verdict rests on something you could not verify. With no decisions and nothing unverified, go to Step 4.

## Step 4: Apply

Make the fixes and the options the user chose. Follow the repo's own instructions for each file you touch. Update every place that restates what you changed: docs, code comments, the PR body.

Verify each change the way you validated its comment. The planted violation now fails, the sample input gives the right result, and the full test and lint suites pass.

Commit in logical groups, in the repo's commit convention, so each reply can cite a SHA. Push the branch before you reply, because the replies cite the commits.

Record each decision where its readers look:

- The linked issue's plan no longer holds: edit the issue body so it states the plan as it now is.
- The user keeps scope beyond the issue: post one comment on the issue that lists each addition and why it is there.
- A fix made a line of the PR body untrue: edit that line.

Done when each fix and each chosen option is committed, pushed and verified, and the issue and the PR body match the code.

## Step 5: Reply

If `~/.claude/skills/writing-line/` exists, gate the replies first. Follow Step 4 of `${CLAUDE_PLUGIN_ROOT}/skills/post-comments/SKILL.md`, and write the bodies to `ai-swap/drafts/technical/pr-$ARGUMENTS-replies.md`.

Reply once to each work-list comment, in its thread:

```bash
gh api -X POST repos/{owner}/{repo}/pulls/$ARGUMENTS/comments/{id}/replies -f body='...'
```

Answer a work-list issue comment or review body with one `gh pr comment $ARGUMENTS`, and quote the line you answer.

Each reply is **terse**: the outcome first, then at most two short sentences of reason. Keep it under 50 words. Write the way a colleague answers in a hallway: plain words, active voice, the point and nothing else. The commit and the diff carry the detail, so the reply names what changed and stops.

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
