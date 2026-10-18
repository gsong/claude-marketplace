# Coding standards

Reviewers apply these rules to a diff. Each one is a judgement call. A rule a script can check belongs in `mise run lint` instead.

## `cowork:build` skill

`plugins/cowork/skills/build/` is plain Markdown guidance for a plugin author. It has no tests, so review carries its whole bar.

### Evidence marks

- Every claim carries a mark from the legend in `SKILL.md` "Freshness". The legend is the only place a mark is defined. `[V, user report]` is one of its marks.
- A consequence drawn from verified sources is an inference. Mark it `[I]`, or `[I, strong]`, even when every source it rests on is `[V]`.
- A Claude Code doc is `[I]` evidence for Cowork until a Cowork page or a live test agrees.
- When a doc and a live test disagree, keep both side by side and mark the claim `[V, conflicting]`. Neither one overwrites the other.
- A live claim carries its test date, such as `[V, live 2026-10-17]`, or a date range.
- An absence claim (`[V: absence]`, "no doc says") added or changed in a diff is rechecked by grep against `mise run docs:mirror` output.
- A design step or a Defaults row in `SKILL.md` that summarizes a reference needs no mark of its own. The reference carries it.

### Sources

- The skill names no private source: no client, product or test names from the test notes, no private document titles, and no claude.ai chat URLs.
- The legend's sentence "The test notes are private" is the one sanctioned pointer to them. Keep it.
- Write each change as guidance for any plugin author. Drop a finding that holds only for the site or product it was tested on.

### Framing and words

- Claude Code is the baseline. The skill covers what changes when a plugin must also run in Cowork. Where the two differ, a reference gives the Claude Code side beside the Cowork rule.
- Add a Claude Code fact only when it changes what the author builds or tests. Link Claude Code's docs for the rest.
- Use the terms in `CONTEXT.md`. A surface is Claude Code or Cowork. Claude Desktop, the claude.ai web app and mobile are apps.
- Chat-only facts live only in `packaging.md`'s Chat section. Its note to drop the section once Team and Enterprise merge Chat into Cowork is intended.
