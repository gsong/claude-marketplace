---
name: gs:utilities:date
description: Use this skill when you need to calculate dates or datetimes based on natural language descriptions. Examples:\n\n<example>\nContext: User needs to know what date it was 7 days ago for a git log command.\nuser: "Show me commits from last week"\nassistant: "I need to calculate the date from 7 days ago. Let me use the /gs:utilities:date skill."\n<Skill tool call: "/gs:utilities:date">\n</example>\n\n<example>\nContext: User is writing code that needs a timestamp from 3 hours ago.\nuser: "I need to filter logs from the last 3 hours"\nassistant: "I'll use the /gs:utilities:date skill to get the timestamp from 3 hours ago."\n<Skill tool call: "/gs:utilities:date">\n</example>\n\n<example>\nContext: User mentions a relative date in their request.\nuser: "Create a report for last month's data"\nassistant: "I need to determine the date range for last month. Let me use the /gs:utilities:date skill."\n<Skill tool call: "/gs:utilities:date">\n</example>\n\n<example>\nContext: Proactively calculating dates when scheduling or planning.\nuser: "Schedule this task for next Monday"\nassistant: "I'll use the /gs:utilities:date skill to determine next Monday's date."\n<Skill tool call: "/gs:utilities:date">\n</example>
tools: Bash, Read, Glob, Grep
---

Calculate the requested date or datetime using BSD `date` commands (macOS). Return only the calculated value. If a request is ambiguous (e.g., "last week" could mean 7 days ago or the previous calendar week), ask for clarification.

Anchor every relative calculation to the actual current date rather than an assumed one. Let `date` read the clock (e.g. `date -v-7d`) instead of computing from a date you assume is today — this is what keeps the result correct regardless of when the skill runs.

**This skill is a helper step.** After calculating and returning the date value, continue with whatever task prompted the calculation. Do not treat the date result as a final response.

## Output

Return only the calculated value. Do not show the command used. Example:

```
2025-10-02
```

When this calculation is part of a larger task, use the value to continue that task rather than treating the output as a final response.

## Command Standards

- Use BSD date syntax (macOS compatible)
- Use `-v` flags for relative date calculations
- Use `-I` or `-Iseconds` for ISO 8601 formats
- Use `-u` flag when UTC time is needed
- Chain `-v` flags for complex calculations (e.g., `date -v-1m -v1d` for first day of last month)
- Default to YYYY-MM-DD format unless otherwise specified
- Verify timezone handling: use `-u` for UTC, omit for local time

## Common Calculation Patterns

**Relative Days**: Use `-v±Nd` (e.g., `-v-7d` for 7 days ago)
**Relative Weeks**: Use `-v±Nw` (e.g., `-v-2w` for 2 weeks ago)
**Relative Months**: Use `-v±Nm` (e.g., `-v+1m` for next month)
**Relative Years**: Use `-v±Ny` (e.g., `-v-1y` for last year)
**Weekdays**: Use `-v+day` or `-v-day` (e.g., `-v+mon` for next Monday)
**Hours**: Use `-v±NH` (e.g., `-v-3H` for 3 hours ago)
**Minutes**: Use `-v±NM` (e.g., `-v+45M` for 45 minutes from now)
**First day of month**: `-v1d` (e.g., `date -v-1m -v1d` for the first of last month)
**Last day of month**: jump to the first of next month, then back a day (e.g., `date -v1d -v+1m -v-1d` for the last day of this month)

## Edge Cases

- Month/year boundaries (e.g., "30 days ago" when current date is early in month)
- Leap years when calculating year-relative dates
- Weekday flags count _today_ as a match: `-v+mon` run on a Monday returns that same Monday, not the following one. When the user clearly means the _upcoming_ weekday, step forward a day first (e.g., `date -v+1d -v+mon`). The order of `-v` flags matters — they apply left to right, so `-v+1d -v+mon` and `-v+mon -v+1d` give different results.
- Ambiguous requests like "last week" -- clarify before calculating

Be concise. Lead with the value.
