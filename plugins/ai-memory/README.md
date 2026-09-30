# ai-memory

Session memory and project instruction management for Claude Code.

## Skills

| Skill               | Description                                                                                                                 |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `/ai-memory:save`   | Write a handoff note so the next session can resume this one's work ("write handoff notes", "before we wrap up")            |
| `/ai-memory:review` | Audit the project CLAUDE.md for token cost against value and report keep/condense/remove edits ("is my CLAUDE.md too long") |

`save` uses `/utilities:date` (from the `utilities` plugin) when installed; otherwise it falls back to plain `date`.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install ai-memory@gsong-marketplace
```
