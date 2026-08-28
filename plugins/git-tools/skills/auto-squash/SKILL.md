---
name: "gs:git-tools:auto-squash"
description: "Classifies each uncommitted change to its originating branch commit, creates fixup commits, and runs an autosquash rebase. Use when the user says \"fold these changes into my earlier commits\", \"fixup my commits\", \"clean up my branch\", or invokes /gs:git-tools:auto-squash."
argument-hint: "[base-branch]"
---

# Smart fixup and auto-squash

Distribute uncommitted changes across the current branch's commits via fixup, creating new commits for anything that doesn't match. Accepts an optional base branch argument: `$ARGUMENTS`

## 1. Pre-flight checks

1. Run `git status --porcelain` — if there are no uncommitted changes (modified, untracked, or deleted files), stop and inform the user
2. Run `git diff --cached --quiet` — if there are already-staged changes, stop the skill and tell the user to stash or commit them first. This skill takes exclusive control of the index to safely verify each fixup's contents; a pre-existing staged layout (e.g., partial hunks from `git add -p`) cannot survive the per-group staging and recovery cycle.

## 2. Determine branch scope

1. **Base branch**: If an argument was provided, use it as the base branch. Otherwise, infer:
   - For each local branch (excluding the current one), compute `git merge-base <branch> HEAD` then `git rev-list --count <merge-base>..HEAD`
   - The branch with the fewest commits ahead of the merge-base is the likely parent
   - On ties, consult `git reflog show HEAD` for a `checkout: moving from <parent> to <current>` entry to disambiguate
   - Fall back to `main` if inference is ambiguous or fails
   - **Always confirm**: Show the inferred base branch to the user and ask for confirmation before proceeding — getting this wrong means fixup commits target the wrong history
2. **Fork point**: `git merge-base HEAD <base-branch>` — if this fails or returns no result (e.g., on the base branch itself), skip to step 5 and treat all changes as new commits
3. **Branch commits**: `git log --oneline <fork-point>..HEAD` — if empty (HEAD equals fork point), skip to step 5 and treat all changes as new commits
4. **Uncommitted changes**: `git status --porcelain` to list all modified, untracked, and deleted files

## 3. Classify changes and map to commits

For each uncommitted change, determine its fixup target:

1. **Direct match**: Run `git log --oneline <fork-point>..HEAD -- <file>`
   - One commit found → use it as the fixup target
   - Multiple commits found → examine the diff and commit messages to pick the most appropriate target
2. **Logical match** (file has no direct branch history): Examine the change and branch commit messages/diffs to determine if it logically belongs with a branch commit:
   - A new test file for a feature added in a branch commit
   - A new config file required by a branch commit's changes
   - A deletion of a file made obsolete by a branch commit
   - A modification that supports or completes work from a branch commit
3. **No match**: No direct or logical association → will become a new commit

Group all matched files by their target commit SHA.

## 4. Create fixup commits

Before the loop, capture the starting HEAD sha: `start_sha=$(git rev-parse HEAD)`. This lets the skill cleanly unwind every fixup created during this run if any verification fails.

For each target commit group:

1. Stage the relevant files with `git add <files>` (this also stages deletions when the file is absent from the working tree)
2. If the changes meaningfully alter the commit's purpose or scope, compose a new commit message reflecting the combined change and run `git commit --fixup=amend:<SHA> -m "<new message>"`. This creates an `amend!` commit that squashes the staged content **and** replaces the target's message on rebase.
   - Do **not** use `--fixup=reword:<SHA>` here — `reword:` is shorthand for `--fixup=amend:<SHA> --only` and silently ignores staged content, leaving it to leak into a subsequent commit.
   - `-m` is the only message flag `--fixup` accepts. `-F` is rejected outright (`fatal: options '-F' and '--fixup' cannot be used together`), so pass a multi-line body through `-m`, which takes embedded newlines — not through a heredoc.
   - If `-m` is rejected (older git), or you need a heredoc, fall back to two steps: `GIT_EDITOR=true git commit --fixup=amend:<SHA>`, then `git commit --amend` to set the message. **The amended message must keep the `amend!` header line the first step generated** — that line is what autosquash matches on. Write the whole message in this shape:

     ```
     amend! <target's original subject>

     <new subject>

     <new body>
     ```

     Everything after the first blank line replaces the target's message; the `amend!` line itself is consumed by the rebase. Overwrite the whole message and the commit stops being an `amend!` commit — autosquash no longer recognizes it and leaves it sitting as an ordinary commit on top, with the target unchanged.
3. Otherwise, use `git commit --fixup <SHA>`
4. **Verify the `amend!` header survived.** Only when you used `--fixup=amend:` — run `git log -1 --format=%s` and confirm the subject starts with `amend! `. If it does not, the message got clobbered; rewrite it with `git commit --amend` in the shape above before going on. This is a message defect, not a content defect — do not unwind for it.
5. **Verify the fixup captured the expected files.** Run `git show --name-only --format= HEAD` and compare against the files you just staged for this group. If the lists differ (missing or extra paths):
   - Run `git reset --mixed <start_sha>` to unwind every fixup commit created during this run (including earlier groups that already succeeded). This restores HEAD to its pre-skill state and leaves all changes unstaged in the working tree — nothing is lost.
   - Tell the user: `Fixup for <SHA> captured <actual> but expected <staged>. I've unwound all fixups from this run; your changes are back in the working tree. Use the gs:git-tools:commit skill to commit them manually.`
   - Stop the skill — do not continue iterating and do not proceed to step 6.

## 5. Create new commits

For any remaining unmatched files:

1. Stage the files with `git add <files>`
2. Create commit(s) with appropriate conventional commit messages (see the gs:git-tools:commit skill for message format) — group by feature area or change type, preferring fewer cohesive commits over many tiny ones

## 6. Rebase (conditional)

**Only if at least one fixup commit was created in step 4:**

This rebase rewrites the branch's history. Before running it, check whether the branch is shared: `git rev-parse --abbrev-ref @{upstream}` succeeding means the branch is pushed and someone else could be working from it — warn the user if so. (Don't use `git branch -r --contains HEAD` here: the fixup commits just created make HEAD unreachable from any remote, so it always comes back empty.)

```
GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash --rebase-merges <fork-point>
```

- `GIT_SEQUENCE_EDITOR=true` accepts the reordered todo list without opening an editor
- `--rebase-merges` preserves merge commits if any exist (no-op on linear branches)
- If the rebase encounters conflicts, stop and inform the user — do not attempt automatic resolution
- After a successful rebase, if the branch was already pushed, tell the user their next push needs `git push --force-with-lease` (never `--force`) since the rewritten history diverges from the remote
