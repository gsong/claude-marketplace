---
name: gs:repo-maintenance:zizmor
description: Use when the user asks to run a security audit on GitHub Actions workflows, check CI/CD pipeline security, scan for workflow vulnerabilities, or use zizmor. Also use when the user invokes /gs:repo-maintenance:zizmor.
---

# Zizmor Security Audit

Run a security audit of GitHub Actions workflows using zizmor, a static analysis tool that identifies vulnerabilities, misconfigurations, and best-practice violations in CI/CD pipelines.

## Process

1. **Pre-flight check:** Verify `.github/workflows/` exists. If not, abort: "This repo doesn't use GitHub Actions workflows."

2. **Run the audit:**
   - Execute: `zizmor --gh-token $(gh auth token) .`
   - Disable sandbox for this command
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

- Zizmor requires GitHub authentication via `gh auth token`
- The tool analyzes `.github/workflows/` directory by default
- Some findings may have auto-fix capabilities
- Prioritize high-severity findings first
- Verify changes don't break existing workflows
