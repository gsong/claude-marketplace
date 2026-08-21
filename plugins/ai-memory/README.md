# ai-memory

Session memory and project instruction management for Claude Code.

## Skills

| Skill                  | Description                                              |
| ---------------------- | -------------------------------------------------------- |
| `/gs:ai-memory:save`   | Capture session work summary for future sessions         |
| `/gs:ai-memory:review` | Analyze CLAUDE.md for effectiveness and token efficiency |

`save` uses `/gs:utilities:date` (from the `utilities` plugin) when installed; otherwise it falls back to plain `date`.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install ai-memory@gsong-marketplace
```
