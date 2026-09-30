# ai-memory

Session memory and project instruction management for Claude Code.

## Skills

| Skill               | Trigger                                    | Description                                                                                    |
| ------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `/ai-memory:save`   | "write handoff notes", "before we wrap up" | Write a handoff note so the next session can resume this one's work                            |
| `/ai-memory:review` | "is my CLAUDE.md too long"                 | Audit the project CLAUDE.md for token cost against value and report keep/condense/remove edits |

`save` uses `/utilities:date` (from the `utilities` plugin) when installed; otherwise it falls back to plain `date`.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install ai-memory@gsong-marketplace
```
