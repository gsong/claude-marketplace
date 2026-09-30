# Voice gate

Runs the `writing` plugin's draft gate on comment bodies before they reach GitHub. Read this only when the `writing:draft` skill is available. The calling skill names the draft file, under `ai-swap/drafts/technical/`.

The gate is a PostToolUse hook. It fires on any write under `ai-swap/drafts/<profile>/`, so writing the bodies there is what runs it.

1. **Write every body** to the draft path the calling skill names, under `ai-swap/drafts/technical/` at the repo root. It is a sibling of `ai-swap/pr-review-{PR}/`, not a child. Pass the Write tool the absolute path. One section per body:

   ```markdown
   ## {index} / `{path}:{line}`

   {body text}
   ```

   Use the **Write tool**, not a shell heredoc. The gate matches `Write`, `Edit`, and `MultiEdit` by tool name, so a `cat >` in Bash writes the file and fires nothing.

   Backtick the path in the heading, exactly as shown. The gate blanks inline code before it runs its rules. A range like `foo.py:12-34` then cannot report as a hyphenated number range. Leave the path bare and your own heading trips that rule.

   Keep the rest of the heading punctuation plain. An em dash in your own section headings counts toward the em dash density the gate reports on the draft as a whole.

   Backtick or fence every code fragment a body quotes, for the same reason. The gate scans neither, which is what keeps a `--` inside quoted code from reporting as a double hyphen.

2. **Read the gate's report and fix what is a real violation.** One misread is expected in this material:

   - A sentence ending inside a closing quotation mark is not seen as a sentence end. Two sentences then merge and report as one long run. Rephrase to move the quote off the boundary, or drop the quotation marks.

   A number-range report is not a misread. It means a `path:line` reference went in unbackticked. Backtick it.

   Say so if a rule misreads the same passage twice. That is a signal the rule is wrong, and the user can retire it.

3. **Fold the corrected text back** onto the bodies, then delete the draft file.

   Deleting it is safe. A second hook keeps a snapshot of each draft so it can tell a
   later edit from the original, and a third sweeps that snapshot at the end of the turn
   once the draft is gone. Leave the file behind instead and the next run on this PR
   diffs its fresh bodies against this run's, which records the whole file as if you had
   corrected it.
