# Zizmor Security Audit

Run a security audit of GitHub Actions workflows using zizmor, a static analysis tool that identifies vulnerabilities, misconfigurations, and best-practice violations in CI/CD pipelines.

## Process

1. **Run the audit:**
   - Execute: `zizmor --gh-token $(gh auth token) .`
   - Disable sandbox for this command
   - Parse the output for security findings

2. **Analyze findings:**
   - If findings are detected, review each one carefully
   - Note the audit type, severity level, and affected workflow files
   - Group findings by type for efficient remediation

3. **Research fixes:**
   - For each unique finding type, fetch the relevant documentation from https://docs.zizmor.sh/audits/
   - Use the WebFetch tool to get specific guidance for each audit type
   - Understand the security implications and recommended mitigations

4. **Propose remediation:**
   - Explain each finding in clear terms
   - Describe the security risk and why it matters
   - Propose specific fixes based on the official documentation
   - Show the exact changes needed in the workflow files

5. **Offer to apply fixes:**
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
