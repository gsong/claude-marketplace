# Scan plugin hooks with a repo check

CI scans plugin hooks with `scripts/scan-hooks.py`. The scan runs in the required `skill-scanner` job, so a finding blocks the merge. We chose a repo check because it was the one option that could block:

- It makes no findings on this repo today.
- It needs no account and sends nothing out.
- It reads `hooks.json` and the scripts that the hooks run.

The issue is #102, and the work is in PR #106.

## Considered Options

- **NVIDIA SkillSpector** with `--no-llm`. It reads `hooks.json`, but it gave 23 high findings on this repo, and all of them looked like false positives. Most came from the deliberate attack strings in `plugins/clef/hooks/test_allow_clef.py`. It has no severity threshold, so it would need a baseline file and could only run as a non-blocking job.
- **Cisco skill-scanner**, which CI already runs. It reads skill directories only, so it never sees a hook. ADR 0001 records that choice.

## Consequences

- The scan matches text only. A script that builds a command name at run time gets past it.
- Files under `skills/` are left to the skill scan. A hook that runs one gets past this scan, unless its command names the file through `${CLAUDE_PLUGIN_ROOT}`.
- The scan has no suppression file. A hook that needs the network changes the rule in the same PR, and the PR says why.
- The repo owns the rules. A new fetch tool or a new script language needs a rule added by hand.
