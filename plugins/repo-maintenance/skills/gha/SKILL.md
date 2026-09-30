---
name: "gha"
description: "Upgrade GitHub Actions workflow dependencies with actions-up, respecting the project's release-age cool-down. Use when the user asks to upgrade GitHub Actions workflow dependencies or use actions-up."
compatibility: "Requires npx and the gh CLI (authenticated), plus network access to the GitHub API."
---

# Upgrade GitHub Actions Dependencies

Upgrade GitHub Actions workflow dependencies using [actions-up](https://github.com/azat-io/actions-up), respecting the project's release-age cool-down.

## Process

### 1. Pre-flight checks

1. **Check for GitHub Actions workflows**: Verify `.github/workflows/` directory exists in the project repo. If not, abort: "This repo doesn't use GitHub Actions workflows."
2. **Check for a root action**: If a root `action.yml`/`action.yaml` exists, add `--recursive` to both actions-up runs.

### 2. Resolve minimumReleaseAge

Read `${CLAUDE_PLUGIN_ROOT}/references/release-age.md` and resolve the effective value — for renovate `packageRules`, match GitHub Actions entries (`matchManagers` includes `"github-actions"`, or patterns like `"actions/*"`). Normalize to **days**, rounding up (e.g., 4320 minutes → 3 days), and report the constraint and its source per the reference.

### 3. Dry-run preview

Run with sandbox disabled — the command needs network access to query the GitHub API:

```bash
GITHUB_TOKEN=$(gh auth token) npx actions-up --yes --dry-run --min-age N
```

- `N` is the resolved minimumReleaseAge in days from step 2
- Present the full output to the user
- **Read the human output.** The JSON report (`--json`) omits the cool-down bucket entirely, reporting `"status": "up-to-date"` with an empty `skipped` array even when an action is being held back. Step 4 depends on the human output.
- Only stop here if the output shows **both** no updates **and** no cool-down line. A `⏳ Skipped ...` line means step 4 has work to do, even when the run also prints `✔ All actions are up to date!`

### 4. Recover cool-down holdbacks

`actions-up` only ever considers each action's newest release. When that release is inside the cool-down, it drops the action instead of falling back to an older release that clears the cool-down. The run then claims everything is up to date while an eligible update exists. The gap is independent of `--min-age`; this step is the only recovery. See [actions-up#54](https://github.com/azat-io/actions-up/issues/54).

The dry-run signals this with a line like:

```
⏳ Skipped 1 update released less than 7 days ago (cool-down, use --min-age 0 to disable)
   • zizmorcore/zizmor-action@6599ee8b7a49aef6a770f63d261d214911a7ce02
```

For each action named there:

1. Resolve the newest release that clears the cool-down (`N` is the same value from step 2):

   ```bash
   gh api "repos/OWNER/REPO/releases" --paginate \
     --jq "[.[] | select(.draft|not) | select(.prerelease|not)
            | select((now - (.published_at|fromdateiso8601)) > (N*86400))] | .[0].tag_name"
   ```

2. Compare that tag against the version comment on the current pin. If it is the same or older, nothing is recoverable — move on.

3. Resolve the tag to a commit SHA. Use the `commits` endpoint, which dereferences annotated tags:

   ```bash
   gh api "repos/OWNER/REPO/commits/TAG" --jq '.sha'
   ```

4. Report it to the user as a recovered update, and carry it into steps 5 and 6 alongside the updates `actions-up` found.

**Cross-check:** if the repo has an open Renovate PR for GitHub Actions, the recovered version should match what Renovate proposes. A mismatch means one of the two resolutions is wrong — investigate before applying.

### 5. Research significant updates

For every major or minor bump, present either the breaking changes found or an explicit 'no changelog located'.

### 6. Confirm with user

Ask the user if they want to apply the updates shown in the dry-run, plus any recovered in step 4. Use the AskUserQuestion tool.

### 7. Apply updates

If the user confirms, run with sandbox disabled — the command needs network access and writes workflow files:

```bash
GITHUB_TOKEN=$(gh auth token) npx actions-up --yes --min-age N
```

- Use the same `--min-age` value as the dry-run
- **Recovered updates from step 4 must be applied by hand** — `actions-up` will not offer them at any `--min-age` setting. Edit the `uses:` line directly, keeping the existing format: `uses: OWNER/REPO@SHA # TAG`
- Present the results showing what was updated
- Summarize: list the workflow files modified and which actions were upgraded, including breaking change highlights from the research step, and mark which entries were recovered by hand

## Important Notes

- This skill updates workflow files in place. Stop after editing; the user commits.
