# Smart fixup and auto-squash

Distribute uncommitted changes across the current branch's commits via fixup, creating new commits for anything that doesn't match. Accepts an optional base branch argument: `$ARGUMENTS`

## 1. Pre-flight checks

1. Run `git status --porcelain` — if there are no uncommitted changes (modified, untracked, or deleted files), stop and inform the user
2. Run `git diff --cached --quiet` — if there are already-staged changes, warn the user that this command will take control of the index and confirm before proceeding

## 2. Determine branch scope

1. **Base branch**: If an argument was provided, use it as the base branch. Otherwise, infer:
   - For each local branch (excluding the current one), compute `git merge-base <branch> HEAD` then `git rev-list --count <merge-base>..HEAD`
   - The branch with the fewest commits ahead of the merge-base is the likely parent
   - On ties, consult `git reflog show HEAD` for a `checkout: moving from <parent> to <current>` entry to disambiguate
   - Fall back to `main` if inference is ambiguous or fails
2. **Fork point**: `git merge-base HEAD <base-branch>` — if this fails or returns no result (e.g., on the base branch itself), skip to step 5 and treat all changes as new commits
3. **Branch commits**: `git log --oneline <fork-point>..HEAD` — if empty (HEAD equals fork point), skip to step 5 and treat all changes as new commits
4. **Uncommitted changes**: `git status --porcelain` to list all modified, untracked, and deleted files

## 3. Classify changes and map to commits

For each uncommitted change, determine its fixup target:

1. **Direct match**: Run `git log --oneline --follow <fork-point>..HEAD -- <file>`
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

For each target commit group:

1. Stage the relevant files with `git add <files>` (this also stages deletions when the file is absent from the working tree)
2. If the changes meaningfully alter the commit's purpose or scope, use `git commit --fixup=reword:<SHA>` to update the message
3. Otherwise, use `git commit --fixup <SHA>`

## 5. Create new commits

For any remaining unmatched files:

1. Stage the files with `git add <files>`
2. Create commit(s) with appropriate conventional commit messages — group by feature area or change type, preferring fewer cohesive commits over many tiny ones

## 6. Rebase (conditional)

**Only if at least one fixup commit was created in step 4:**

```
GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash --rebase-merges <fork-point>
```

- `GIT_SEQUENCE_EDITOR=true` accepts the reordered todo list without opening an editor
- `--rebase-merges` preserves merge commits if any exist (no-op on linear branches)
- If the rebase encounters conflicts, stop and inform the user — do not attempt automatic resolution
