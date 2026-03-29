---
name: commit
description: Use when the user wants to commit changes with conventional commit format, or when the user invokes /commit.
---

# Commit Changes

You are tasked with committing changes in the current project repository. Follow these guidelines:

## Core Requirements

- Use conventional commit format (feat:, fix:, docs:, refactor:, test:, chore:)
- Always use `git push --force-with-lease` instead of `git push --force`
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

## Important Notes

- Never commit unless explicitly asked
- Check for sensitive information before committing
- If pre-commit hooks modify files, amend the commit to include those changes
- Do not push to remote unless explicitly requested
