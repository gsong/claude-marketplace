---
name: "gs:repo-maintenance:zizmor"
description: "Run a zizmor security audit of GitHub Actions workflows and offer fixes for the findings. Use when the user asks to run a security audit on GitHub Actions workflows, check CI/CD pipeline security, scan for workflow vulnerabilities, or use zizmor. Also use when the user invokes /gs:repo-maintenance:zizmor."
compatibility: "Requires zizmor. The gh CLI and network access enable its online audits; without them it falls back to --offline."
---

# Zizmor Security Audit

Run a security audit of GitHub Actions workflows using zizmor, a static analysis tool that identifies vulnerabilities, misconfigurations, and best-practice violations in CI/CD pipelines.

## Process

1. **Pre-flight checks:**
   - **Check zizmor is available**: Run `command -v zizmor`. If not installed, abort: "zizmor is not installed — see https://docs.zizmor.sh/installation/"
   - **Check there's something to audit**: Verify `.github/workflows/` exists, or a root `action.yml`/`action.yaml`. If neither, abort: "This repo has no GitHub Actions workflows or action definitions to audit."

2. **Run the audit:**
   - If `gh` is authenticated, execute: `GH_TOKEN=$(gh auth token) zizmor .` — passing the token via the environment keeps it out of process listings
   - If `gh` isn't authenticated, fall back to `zizmor --offline .` and note to the user that online audits were skipped
   - Disable sandbox for this command — online audits need network access to the GitHub API
   - Present the full audit output to the user before proceeding

3. **Research findings:**
   - For each unique finding type, fetch the relevant documentation from https://docs.zizmor.sh/audits/
   - Use the WebFetch tool to get specific guidance for each audit type
   - Group findings by type, severity, and affected workflow files
   - Present findings to the user with security implications and recommended mitigations

4. **Offer to apply fixes:**
   - Ask if the user wants to apply the recommended fixes
   - If approved, make the necessary changes to the workflow files
   - Re-run the audit to verify the fixes resolved the issues

## Output

Present findings in a structured format:

- **Summary:** Total findings by severity level
- **Detailed findings:** For each issue:
  - Audit name and severity
  - Affected file and location
  - Security implication
  - Recommended fix with code example
- **Next steps:** Clear action items for remediation

## Important Notes

- GitHub authentication is only needed for zizmor's online audits — `--offline` (or `--no-online-audits`) runs the static checks without it
- Auditing `.` collects workflow files, `action.yml`/`action.yaml` definitions, and `dependabot.yml` (zizmor's default `--collect` behavior) — not just `.github/workflows/`
- zizmor's `--fix` flag is experimental — prefer manual edits, which keep the user in control of each change
- Prioritize high-severity findings first
- Verify changes don't break existing workflows
