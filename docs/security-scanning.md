# Security scanning

CI runs two scans: the skill scan and the hook scan. Both run in the same CI job, on every pull request and push to `main`. A failed scan blocks the merge.

## Skill scan

CI scans every skill in `plugins/` and `.claude/skills/` with [Cisco skill-scanner](https://github.com/cisco-ai-defense/skill-scanner). It fails on a high or critical finding. The scan runs offline with rules only, so it needs no account and sends nothing out. The report goes to GitHub code scanning, where medium and low findings show as alerts.

Run the same scan locally:

```
mise run scan:skills
```

Pass a path to also write a SARIF report. The scan reads a copy of the files that git tracks or does not ignore. Ignored files such as `__pycache__` stay out. A local run also reads untracked files, which CI does not have. So a local run can report findings that CI does not.

To triage a finding:

- A real risk: fix the skill.
- A false positive: add a suppression to `skill-scanner-policy.yaml`. Scope it by `rule_id`, `skills`, and `paths`, and give a reason.
- A rule that can never apply here: add it to `disabled_rules`.

The scan has limits:

- It reads skill directories only. The hook scan covers plugin hooks, but a script outside `skills/` that no hook runs goes unscanned.
- Rules alone catch 7.7% of malicious skills by Cisco's own count. The scan finds known patterns only, and it does not replace a review.

## Hook scan

CI scans the plugin hooks with `scripts/scan-hooks.py`. The hook scan reads `hooks/hooks.json` and any hooks that `plugin.json` declares. It reads each hook command, and every code file that a command or a scanned file names. It skips files under `skills/`, because the skill scan reads them. The CI log lists each file it scanned.

The hook scan fails when a line does one of these things:

- It calls a network tool, such as `curl`, `wget` or `nc`.
- It pipes text into a shell, or into an interpreter that reads its program from the pipe.
- It runs a stream or command output as code, such as `source <(…)` or `eval "$(…)"`.
- It opens a connection through `/dev/tcp/` or `/dev/udp/`.
- It loads a network module, such as Python's `urllib`, Node's `https` or Perl's `LWP`, or calls `fetch`.
- It fetches code or packages, such as `uvx`, `npx`, `npm install`, `pip install`, `git clone`, or a script header that lists dependencies for uv.

It also fails on an `http` hook. It fails on a command that runs a script by a path outside `${CLAUDE_PLUGIN_ROOT}`, or whose script is missing. It fails on a file it cannot read or parse. A whole-line comment does not count. Run the same scan locally:

```
mise run scan:hooks
```

The hook scan has no suppression file. If a hook needs the network, change the rule in `scripts/scan-hooks.py` and say why in the pull request. The hook scan has these limits:

- It matches text only. It does not detect a command name that a script builds at run time.
- It does not detect a hook that runs a script under `skills/`, unless the command names that script through `${CLAUDE_PLUGIN_ROOT}`.
- It checks network use and code fetches only. It does not detect a hook that reads secrets or deletes files.
