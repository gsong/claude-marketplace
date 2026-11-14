# utilities

General-purpose utilities for Claude Code.

## Skills

| Skill             | Trigger                                                               | Description                                                                         |
| ----------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `/utilities:date` | "commits from last week", "logs from the last 3 hours", "30 days ago" | Calculate dates and datetimes from natural language using BSD date commands (macOS) |

## Prerequisites

- macOS, or another system with BSD `date`. The recipes use `date -v`, which GNU `date` on Linux does not support.

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install utilities@gsong-marketplace
```
