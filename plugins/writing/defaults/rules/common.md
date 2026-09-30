# Voice rules — common

Every profile gets these. The gate loads this file first, then the profile's
own file, so a profile file holds only what changes with the audience.

A rule belongs here when it is true of all three profiles. A rule shared by two
stays duplicated in those two. "Common" has to mean all of them, or the reader
cannot trust the word.

## Greppable

The gate reads the block below, and the matching block in each profile file.
Each line is tab-separated fields. The kind comes first and the message last.
`re` takes one regular expression. `maxwords` takes one number. `density` takes
a regular expression, a floor count, and a rate per thousand words: it reports
only when both are exceeded. Lines starting with `#` are comments. Fenced code
blocks and front matter in the draft are never checked.

`maxwords` changes with the audience, so it is never set here. The profile file
is parsed second, and the last `maxwords` wins.

```rules
# Punctuation
density	(?:—|&mdash;)	4	4	em dashes are frequent here; a colon usually does the job, and a pair bracketing an aside is never right
re	;	semicolon; use a period or a colon
re	(?<![\d-])\d+\s*[-—]\s*\d+(?![\d-])	number range with a hyphen or em dash; use an en dash (–)
re	\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*[-—]\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)	date range with a hyphen or em dash; use an en dash (–)

# Banned constructions — AI tells
re	\b[Dd]elve	"delve"; say "look at"
re	\b[Ll]everag(e|es|ing|ed)\b	"leverage" as a verb; say "use"
re	\b[Uu]tiliz(e|es|ing|ed)\b	"utilize"; say "use"
re	\b(seamless|robust|comprehensive|cutting-edge|game-chang|synerg)	marketing adjective; name the property
re	\b([Bb]eing straight|[Tt]o be (honest|blunt|straight)|[Ff]rankly)\b	telling the reader you are being candid; just be candid

# American English
re	\b(colou?r|behaviour|favour|honour|labour|organis|recognis|analys|prioritis|customis|optimis|apologis|realis|summaris)	British spelling; use American
re	\b(centre|licence|defence|whilst|amongst)\b	British spelling; use American
```

## Judgment

There is none here on purpose. The Judgment bullets stay in the profile files,
even where they repeat word for word. The gate never reads them, and the model
reads one profile file top to bottom. Splitting them would buy nothing and cost
a second read.
