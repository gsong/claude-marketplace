# Claude Code plugin marketplace

A marketplace of Claude Code plugins, with CI checks that keep each plugin safe to install.

## Language

### Plugin contents

**Skill directory**:
The directory under a plugin's `skills/` that holds one skill's `SKILL.md` and the files beside it.

**Outside file**:
A plugin file outside every skill directory that a skill runs or loads. Examples are a script under `scripts/` and a Markdown file under `references/`.
_Avoid_: supporting file, shared file

### Security scans

**Skill scan**:
The CI check that runs Cisco skill-scanner on each skill directory, together with the outside files that skill uses.

**Hook scan**:
The CI check that reads each plugin hook command, and the code files it names, for network use and downloads.

### Clef opportunities

**Clef**:
Cloudflare's decision model. It reads a state of text or JSON, plus up to four images, and answers typed questions about it. A typed question takes a yes/no (`noul`), pick-one (`choice`) or rating (`score`) answer.

**Typed question**:
A question in the form Clef receives: a type, instructions, and each `choice` option or `score` level. Any other question is not typed.

**Decision point**:
One kind of item, such as an email or a ticket. It holds every typed question a system asks about each item again and again at runtime. One item's facts fit in one Clef state.
_Avoid_: candidate

**Fit test**:
The test, run on each decision point, of whether that decision point suits Clef. A decision point fits only if it passes on stakes, latency, fallback and a true-answer source besides Claude. Clef runs on the system's own hardware by default, and in Cloudflare's cloud only when that hardware cannot run it.

**Reject pattern**:
A named shape that excludes a question from a decision point, or rules out an experiment design. An example is a second opinion on facts Claude has already read.

**Verdict**:
The recorded outcome for a question or a decision point. A dropped question gets its reason, such as "not typed" or a reject pattern. A decision point gets "fits", "fits, pending a latency measurement" or "no fit", which names what failed.
