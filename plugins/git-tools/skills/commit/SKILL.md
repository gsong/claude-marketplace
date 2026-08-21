---
name: "gs:git-tools:commit"
description: "Groups staged and unstaged changes into logical commits, runs lint/typecheck first, and writes conventional-commit messages focused on why. Use when the user says \"commit this\", \"commit my changes\", \"make a commit\", or invokes /gs:git-tools:commit."
---

# Commit Changes

You are tasked with committing changes in the current project repository. Follow these guidelines:

## Core Requirements

- Use conventional commit format (feat:, fix:, docs:, refactor:, test:, chore:, style:, perf:)
- If the user asks you to push, use `git push --force-with-lease`, never `--force`
- Separate changes into logical commits if multiple distinct changes exist
- Run lint and typecheck commands before committing if available

## Process

1. Run `git status`, `git diff`, and `git diff --cached` to understand all changes (staged and unstaged)
2. Run lint and typecheck commands if available (check `package.json` scripts, `Makefile`, etc.)
   - Fix any issues before proceeding
3. Analyze changes and group them logically:
   - New features (feat:)
   - Bug fixes (fix:)
   - Documentation updates (docs:)
   - Code refactoring (refactor:)
   - Tests (test:)
   - Maintenance tasks (chore:)
   - Formatting/style-only changes (style:)
   - Performance improvements (perf:)
4. Create separate commits for each logical group
5. Write clear, concise commit messages focusing on "why" not "what"
6. Verify commits with `git log` and `git status`

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

- Do not create the commit prematurely; finish the status/diff review and any lint/typecheck steps first — committing early bakes in problems those steps would have caught
- Only commit the changes the user asked for; leave unrelated changes staged or unstaged as they were — sweeping them in muddies history and surprises the user
- Check for sensitive information before committing — a secret in a commit persists in history even after it's removed from the files
- If pre-commit hooks modify files, amend the commit to include those changes — otherwise the hooks' edits are left sitting uncommitted in the working tree
- Do not push to remote unless explicitly requested — publishing commits is a separate decision the user makes
