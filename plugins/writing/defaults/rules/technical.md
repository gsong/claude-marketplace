# Voice rules — technical

Docs and engineering explainers.

A generic default. A rules directory at `~/.claude/writing-line/rules/`
replaces this whole directory.

## Greppable

`common.md` holds the rules that apply to every profile, and the gate loads it
alongside this file. The field format is documented there. This block holds only
what is specific to docs and engineering explainers.

```rules
# Register — one idea per sentence
maxwords	20	sentence runs over 20 words; split it
re	--	double hyphen; use a period or a comma

# Preamble — the answer starts on line one
re	^(Great|Certainly|Sure|Of course|Absolutely|I'd be happy|Let me start by)	preamble; lead with the outcome

# Banned constructions — AI tells
re	[Ii]t('s| is) (important|worth) (to note|noting)	filler; state the point
re	\b(furthermore|moreover|additionally),	connective filler; start the sentence
re	\b(landscape|realm|tapestry|testament to)\b	metaphor; name the thing
re	[Nn]ot only .* but also	inflated pairing; use one clause
re	\bin (today's|the modern) (world|landscape)	throat-clearing; cut it

# Confidence — verified and inferred must not read alike
re	\b(arguably|somewhat|fairly|rather(?! than\b)) \b	hedge; state it or drop it
re	\b(basically|essentially|simply put)\b	filler qualifier; cut it
density	\b(genuinely|actually|really)\b	4	1.5	intensifier repeated; the sentence is stronger without it
```

## Judgment

The gate cannot check these. They load as context when the skill runs.

- Lead with the outcome or the recommendation. Then give the premise.
- Use the active voice. Name the actor.
- Use one word for one meaning.
- Define an acronym at first use, or drop it.
- Say plainly what you verified and what you inferred.
