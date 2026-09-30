# Voice rules — mixed

Write-ups and presentations for non-technical or mixed audiences.

A generic default. A rules directory at `~/.claude/writing-line/rules/`
replaces this whole directory.

## Greppable

`common.md` holds the rules that apply to every profile, and the gate loads it
alongside this file. The field format is documented there. This block holds only
what is specific to a non-technical or mixed audience.

```rules
maxwords	30	sentence runs over 30 words; split it
re	^(Great|Certainly|Sure|Of course|Absolutely|I'd be happy)	preamble; lead with the outcome
re	[Ii]t('s| is) (important|worth) (to note|noting)	filler; state the point
re	\b(landscape|realm|tapestry|testament to)\b	metaphor; name the thing
density	\b(genuinely|actually|really)\b	4	1.5	intensifier repeated; the sentence is stronger without it
```

## Judgment

The gate cannot check these. They load as context when the skill runs.

- Open with the outcome the reader cares about, not the topic.
- Define every term a non-engineer would stop on, or replace it.
- One idea per paragraph. The first sentence carries it.
