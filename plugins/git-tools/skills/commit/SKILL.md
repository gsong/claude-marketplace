---
name: "commit"
description: "Groups staged and unstaged changes into logical commits, runs lint/typecheck first, and writes conventional-commit messages focused on why. Use when the user asks to commit their changes."
---

# Commit Changes

You are tasked with committing changes in the current project repository. Follow these guidelines:

## Process

1. Run `git status`, `git diff`, and `git diff --cached` to understand all changes (staged and unstaged), and confirm the diff holds no secrets — a secret in a commit persists in history even after it's removed from the files
2. Run lint and typecheck commands if available (check `package.json` scripts, `Makefile`, etc.)
   - Fix any issues before proceeding
3. Group into one commit per logical change, typed per the Examples. Only the changes the user asked for go in; leave unrelated changes staged or unstaged as they were — sweeping them in muddies history and surprises the user. Done when every changed hunk sits in exactly one group or is deliberately left out
4. Create separate commits for each logical group
   - If pre-commit hooks modify files, amend the commit to include those changes — otherwise the hooks' edits are left sitting uncommitted in the working tree
5. Write clear, concise commit messages focusing on "why" not "what"
6. Verify: `git status` shows only what you left out; `git log` shows one commit per group

## Commit Message Format

```
type: brief description

Optional longer explanation of what changed and why.
```

## Examples

- `feat: support OAuth login for enterprise SSO requirement`
- `fix: prevent connection pool exhaustion under concurrent load`
- `docs: clarify rate limiting behavior for API consumers`
- `refactor: simplify payment module for upcoming multi-currency support`
- `test: cover payment edge cases that caused prod incidents`
- `chore: upgrade deps to resolve security advisories`
- `style: apply prettier formatting after config update`
- `perf: cache session lookups to cut checkout latency`

## Important Notes

- Commit only after steps 1-2 complete; committing early bakes in problems those steps would have caught
- Push only when the user asks, and then with `git push --force-with-lease`, never `--force`
