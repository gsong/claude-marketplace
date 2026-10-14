# Usage limits and context budget

Researched 2026-10-11. Marks: **[V]** verified, **[I]** inference.

## What is published

- Paid plans have a session limit that resets every five hours and a weekly
  limit. Settings > Usage shows both.
  https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work,
  https://support.claude.com/en/articles/8325606-what-is-the-pro-plan **[V]**
- No message count or token cap is published for any plan. The only multiples:
  Pro gives "at least 5x more usage per 5-hour session than Free", and Max 5x
  and 20x give five or twenty times Pro. https://claude.com/pricing **[V]**
  State no "runs per day" number as fact.
- claude.ai, Claude Code and Claude Desktop draw on the same limit. **[V]**
- "Tools and connectors are token-intensive." Browsing, running code and
  creating files are usage drivers. "Claude Cowork consumes limits faster than
  Chat." No page gives a factor between chat and browser work.
  https://support.claude.com/en/articles/9797557-usage-limit-best-practices,
  https://claude.com/product/cowork **[V]**
- Newest models on paid plans support up to 1M tokens of context, varying by
  model. **[V]** So the context window is rarely the limit; the usage meter
  is.
- Project content is cached and "counts less against your limits when reused".
  **[V]**

## Measured example

One browsing task, measured 2026-10-11: two page loads plus 16 same-origin
fetches through `javascript_tool`, across two sites. **[V, measured]**

- Untrimmed, the fetches carried about 480 KB (about 120,000 tokens).
- Trimmed inside the page, they returned about 5,000 characters (about 1,300
  tokens).
- One record ran about 1,000 characters raw and 56 trimmed; one calendar event
  ran 4,900 raw and 120 trimmed.
- With skill text, scripts and the final report, new text was about 6,000
  tokens. Each tool call re-reads the conversation, so the processed total
  was likely 100,000 to 200,000 tokens. **[I]** Anthropic does not say how the
  meter weighs cached reads.

On the meter, a browsing chat with 2 page loads, 4 `javascript_tool` or
network calls and one follow-up used about 3 points of a 5-hour Pro session
and about 1 point of the week. It ran on Sonnet 5.5 at Medium effort. A
similar task on Opus 5.5 at Medium measured the same. Settings > Usage shows
the week in whole percents, so that cost is 0.5 to 1.5 points. **[V, live]**

## Trimming rules

- Fetch big pages and JSON inside the page script; return only what the task
  needs.
- Return arrays, not objects with keys, and cut long strings.
- Limit the date range and cap list lengths, so a busy account cannot blow the
  budget.
- Have each script report its returned length, and have the skill re-run in a
  tighter mode above a set size (for example 12,000 characters).
- Read pages as text or screenshots only as a fallback; that route costs
  several times more visits and tokens. **[I]**

## Measure on the user's account

1. Note Settings > Usage (session and weekly percent).
2. Run the task once from a fresh chat, with no screenshots, plus one
   follow-up question.
3. Note Settings > Usage again. The difference is the real cost on that plan
   and model.
