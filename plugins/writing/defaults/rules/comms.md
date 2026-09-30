# Voice rules — comms

Email and Slack.

A generic default. A rules directory at `~/.claude/writing-line/rules/`
replaces this whole directory.

## Greppable

`common.md` holds the rules that apply to every profile, and the gate loads it
alongside this file. The field format is documented there. This block holds only
what is specific to email and Slack.

```rules
maxwords	24	sentence runs over 24 words; split it, unless it carries one idea in one clause
re	^(Great|Certainly|Sure|Of course|Absolutely|I'd be happy|Hope this finds you)	preamble; lead with the ask
re	\b(just wanted to|quick question|circle back|touch base|reach out)\b	filler opener; state the ask
```

## Judgment

The gate cannot check these. They load as context when the skill runs.

- Put the ask in the first sentence. Context comes after.
- Name the deadline and the owner.
- One message, one ask. Split anything longer.
