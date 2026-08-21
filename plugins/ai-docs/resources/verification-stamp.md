Run `git rev-parse HEAD` to get the current commit SHA. Set the first line of each doc being stamped to:

```markdown
<!-- verified-against: [full-commit-sha] -->
```

Replace an existing stamp line; otherwise insert it as the first line.

If `git rev-parse HEAD` fails (no git, no commits), skip stamping.
