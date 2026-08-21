---
name: gs:utilities:date
description: Calculate dates and datetimes from natural-language descriptions — relative days/weeks/months/years, weekdays, hours, timestamps, and date ranges — using macOS `date`. Use whenever a request involves a relative or computed date, e.g. "commits from last week", "logs from the last 3 hours", "last month's report", "schedule this for next Monday", or "30 days ago", including proactively when scheduling or planning.
allowed-tools: Bash
---

Calculate the requested date or datetime using BSD `date` commands (macOS). If a request is ambiguous (e.g., "last week" could mean 7 days ago or the previous calendar week), ask for clarification.

Anchor every relative calculation to the actual current date rather than an assumed one. Let `date` read the clock (e.g. `date -v-7d`) instead of computing from a date you assume is today — this is what keeps the result correct regardless of when the skill runs.

**This skill is a helper step.** After calculating and returning the date value, continue with whatever task prompted the calculation. Do not treat the date result as a final response.

## Output

Return only the calculated value. Do not show the command used. Example:

```
2025-10-02
```

## Command Standards

- BSD/macOS `date` only: these recipes rely on `-v` flags. GNU/Linux `date` uses different syntax (`-d "7 days ago"`) and will error on `-v`; it is not supported here.
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

- Month boundaries: `-v` month arithmetic clamps to the last valid day, so no correction is needed (verified: `-v+1m` on 2026-01-31 gives 2026-02-28, and on 2024-01-31 gives 2024-02-29). Day arithmetic crosses month/year boundaries correctly too.
- Leap years: day arithmetic handles Feb 29 correctly (verified: `-v+1d` on 2024-02-28 gives 2024-02-29), but year arithmetic from Feb 29 does _not_ clamp — `-v+1y` on 2024-02-29 gives 2025-03-01, not 2025-02-28. If the user wants the end of February, step back a day after the year adjustment (verified: `-v+1y -v-1d` on 2024-02-29 gives 2025-02-28).
- Weekday flags count _today_ as a match: `-v+mon` run on a Monday returns that same Monday, not the following one. When the user clearly means the _upcoming_ weekday, step forward a day first (e.g., `date -v+1d -v+mon`). The order of `-v` flags matters — they apply left to right, so `-v+1d -v+mon` and `-v+mon -v+1d` give different results.
- Ambiguous requests like "last week" -- clarify before calculating

Be concise. Lead with the value.
