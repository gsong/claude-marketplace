Establish the doc's baseline, then count changes to its Key Paths since that baseline. Every doc carries its own stamp, so do this per doc.

1. Read the doc's first line. If it is a verification stamp:

   ```markdown
   <!-- verified-against: [full-commit-sha] -->
   ```

   and the SHA is a known commit (`git cat-file -e [sha]^{commit}` succeeds), use that SHA as the baseline. The stamp is the commit the doc was last generated or verified against — it is more precise than the doc's own git history.

2. Otherwise (no stamp, or the SHA is unknown, e.g. after a rebase or in a shallow clone), fall back to the doc's last-modified commit and note in the result that the doc is unstamped:

   ```
   git log -1 --format=%H -- [docs-dir]/[filename].md
   ```

3. For each Key Path that resolved under `[path-root]`, count commits since the baseline:

   ```
   git rev-list --count [baseline]..HEAD -- [path-root]/[key-path]
   ```

   A count greater than zero means potentially stale. Count only paths that resolved: git prints `0` for a path it has never seen, so a zero on an unresolved path is vacuous, never fresh.
