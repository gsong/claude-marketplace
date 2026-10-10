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

### Clef

**Clef**:
Cloudflare's decision model. It reads a state of text or JSON, plus up to four images, and answers typed questions about it. A typed question takes a yes/no (`noul`), pick-one (`choice`) or rating (`score`) answer.

**Typed question**:
A question in the form Clef receives: a type, instructions, and each `choice` option or `score` level. Any other question is not typed.
