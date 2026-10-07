# Reject patterns

A reject pattern is a named shape that drops a question from a decision point, or rules out an experiment design. A drop's verdict names the pattern and the reason, such as "Has an attachment? R11: a rule. Stays in code."

## Checked against each question

- **R1:** a second opinion on facts Claude has already read in the same session. Clef then adds a call and replaces none.
- **R2:** asking Clef to scan or find, not to confirm a named option. "Does this sentence name a product?" scans. "Is 'Atlas' in this sentence a product name?" confirms.
- **R3:** a question of permission or intent that belongs to the user, such as whether to act without asking, or what the user wants.
- **R7:** a task that needs tools, files or history the state does not hold.
- **R10:** code the user does not own, such as a vendored library or a third-party service.
- **R11:** a rule-shaped decision dressed as a judgment. A regex, a lookup or a comparison decides it, so it stays in code.

## Applied in design

These govern the fit test and the experiment design.

- **R4:** rules written into the state. The state holds only the item's facts.
- **R5:** Claude as the only judge of Clef. The F7 judge must be a source of true answers besides Claude.
- **R6:** Clef as the sole authority for an irreversible or high-stakes act. The F6 gate fails on it.
- **R8:** treating `confidence` or the margin as a calibrated probability. Thresholds gate on `probabilities`.
- **R9:** claiming savings without measuring Claude's tokens. The experiment measures the tokens and money of the call Clef replaces.
