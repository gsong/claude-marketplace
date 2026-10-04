# Scan skills with Cisco skill-scanner

CI scans every skill with Cisco skill-scanner 2.2.0 and fails on a high or critical finding. The scan uses rules only, so it runs offline. We chose it because it was the one candidate that met three needs:

- It needs no account.
- It sends no skill text out.
- It has a severity threshold.

The evaluation is in PR #103.

## Considered Options

- **huifer/skill-security-scan**, proposed in #12. Its repo stopped after three commits on one day. Its PyPI package fails on the first run, because the package leaves out its rules file.
- **Snyk Agent Scan**, proposed in #12. It needs a Snyk account and sends skill files to Snyk's service. Its CI mode fails on any finding, with no severity threshold.
- **NVIDIA SkillSpector.** It reads hooks, which Cisco's scanner does not. It has no severity threshold, and it gave 23 high findings on this repo. All of them looked like false positives.

## Consequences

- The scan never reads plugin hooks. A separate repo check scans them. ADR 0002 records that choice.
- The scan never reads a script that a skill calls from outside its skill directory. #104 tracks that.
- Rules find known patterns only. The scan runs no model pass, so it does not replace a review.
