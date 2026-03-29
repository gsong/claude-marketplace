# utilities

General-purpose utilities for Claude Code — date calculations, dependency management, and security auditing.

## Skills

| Skill             | Trigger                                                | Description                                                                         |
| ----------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| `date-calculator` | "calculate date", "what date was", "days ago/from now" | Calculate dates and datetimes from natural language using BSD date commands (macOS) |

## Commands

| Command                           | Description                                           |
| --------------------------------- | ----------------------------------------------------- |
| `/utilities:upgrade-dependencies` | Upgrade project dependencies using pnpm               |
| `/utilities:zizmor-audit`         | Run zizmor security audit on GitHub Actions workflows |

## Prerequisites

- [pnpm](https://pnpm.io/) — for dependency upgrades
- [zizmor](https://docs.zizmor.sh/) — for GitHub Actions security auditing

## Installation

```
/plugin marketplace add gsong/claude-marketplace
/plugin install utilities@gsong-marketplace
```
